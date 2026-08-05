"""
src/apuracao_faturamento.py — Apuração de faturamento de manicures e assistentes.
RN-12 (manicures) e RN-13 (assistentes, Raynara desligada ago/26).
Uso: python src/apuracao_faturamento.py <YYYY-MM> <manicures|assistentes>
"""
import argparse
import os
import sqlite3
import sys
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "db", "gansos.db")

# Vigência retroativa cobre todo o período jan–jul/2026; revisão formal 2026-08-05 (D2)
_VIGENCIA_INICIO = "2026-01-01"

# RN-12: manicures
_PARAMS_MANICURES = [
    ("bronze_meta",  "6000"),
    ("bronze_premio", "150"),
    ("prata_meta",   "8000"),
    ("prata_premio",  "300"),
    ("ouro_meta",   "10000"),
    ("ouro_premio",   "500"),
]

# RN-13: assistentes
_PARAMS_ASSISTENTES = [
    ("bronze_meta",  "2500"),
    ("bronze_premio", "100"),
    ("prata_meta",   "3500"),
    ("prata_premio",  "200"),
    ("ouro_meta",    "5000"),
    ("ouro_premio",   "350"),
]

MANICURES = [
    "Hilda Araújo Parga",
    "Esmeralda Belém dos Santos",
    "Isaura Jéssica dos Santos Alves",
    "Rayssa Leite Da Silva Soares",
    "Safira Belém dos Santos",
]

ASSISTENTES = [
    "Maria Aparecida Florencio de França",
    "Suzan Nayara Garcez Silva",
    "Ana Mayra Coelho De Jesus",
    "Raynara de Cassia Cutrim Dos Santos",
]

# Raynara desligada a partir de ago/2026 (RN-13)
DESLIGAMENTOS = {
    "Raynara de Cassia Cutrim Dos Santos": "2026-08",
}

# Outras funções conhecidas (não manicure nem assistente) para seed completo
RECEPCAO_CAIXA = [
    "Thamires Ferreira",
    "Leandro Jose França Nunes",
]

_POLITICA_FUNCAO = {
    "manicures":   "manicure",
    "assistentes": "assistente",
}


# ---------------------------------------------------------------------------
# Seed
# ---------------------------------------------------------------------------

def seed_parametros(con: sqlite3.Connection) -> None:
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for politica, params in [("gratificacao_manicures", _PARAMS_MANICURES),
                              ("gratificacao_assistentes", _PARAMS_ASSISTENTES)]:
        for chave, valor in params:
            existe = con.execute(
                "SELECT 1 FROM parametros WHERE politica=? AND chave=? AND vigencia_inicio=?",
                (politica, chave, _VIGENCIA_INICIO),
            ).fetchone()
            if not existe:
                con.execute(
                    """INSERT INTO parametros
                       (politica, chave, valor, vigencia_inicio, vigencia_fim, alterado_por, alterado_em)
                       VALUES (?, ?, ?, ?, NULL, 'sistema', ?)""",
                    (politica, chave, valor, _VIGENCIA_INICIO, agora),
                )
    con.commit()


def seed_funcoes(con: sqlite3.Connection) -> None:
    for nome in MANICURES:
        con.execute(
            "UPDATE profissionais SET funcao='manicure' WHERE nome_sistema=? AND funcao='pendente'",
            (nome,),
        )
    for nome in ASSISTENTES:
        con.execute(
            "UPDATE profissionais SET funcao='assistente' WHERE nome_sistema=? AND funcao='pendente'",
            (nome,),
        )
    for nome in RECEPCAO_CAIXA:
        con.execute(
            "UPDATE profissionais SET funcao='recepcao_caixa' WHERE nome_sistema=? AND funcao='pendente'",
            (nome,),
        )
    con.commit()


# ---------------------------------------------------------------------------
# Apuração
# ---------------------------------------------------------------------------

def _get_params_fat(politica: str, mes: str, con: sqlite3.Connection) -> dict | None:
    """Parâmetros de gratificação vigentes no mês para a política. None se ausentes."""
    nome_politica = f"gratificacao_{politica}"
    mes_inicio = mes + "-01"
    rows = con.execute(
        """SELECT chave, valor FROM parametros
           WHERE politica = ?
             AND vigencia_inicio <= ?
             AND (vigencia_fim IS NULL OR vigencia_fim > ?)
           ORDER BY vigencia_inicio DESC""",
        (nome_politica, mes_inicio, mes_inicio),
    ).fetchall()
    if not rows:
        return None
    params: dict[str, str] = {}
    for chave, valor in rows:
        params.setdefault(chave, valor)
    return params


def _nivel_gratificacao(fat: float, params: dict) -> tuple[str | None, float]:
    niveis = [
        ("Ouro",   float(params["ouro_meta"]),   float(params["ouro_premio"])),
        ("Prata",  float(params["prata_meta"]),  float(params["prata_premio"])),
        ("Bronze", float(params["bronze_meta"]), float(params["bronze_premio"])),
    ]
    for nome, meta, premio in niveis:
        if fat >= meta:
            return nome, premio
    return None, 0.0


def apurar_faturamento(mes: str, politica: str, con: sqlite3.Connection) -> list[dict]:
    """
    Retorna faturamento de cada profissional da política no mês informado.
    politica: 'manicures' ou 'assistentes'
    mes: 'YYYY-MM'
    Aplica RN-12/13: nível e gratificação se parâmetros existirem.
    Aplica RN-13: exclui assistentes desligadas cujo desligamento seja >= mes.
    """
    funcao = _POLITICA_FUNCAO.get(politica)
    if not funcao:
        raise ValueError(f"Política inválida: {politica!r}. Use 'manicures' ou 'assistentes'.")

    params = _get_params_fat(politica, mes, con)

    rows = con.execute(
        """SELECT p.nome_sistema, ROUND(SUM(v.valor), 2) as fat
           FROM vendas v
           JOIN profissionais p ON p.id = v.profissional_id
           WHERE p.funcao = ?
             AND v.tipo = 'Serviço'
             AND strftime('%Y-%m', v.data_hora) = ?
           GROUP BY p.nome_sistema
           ORDER BY fat DESC""",
        (funcao, mes),
    ).fetchall()

    resultado = []
    for nome, fat in rows:
        deslig = DESLIGAMENTOS.get(nome)
        if deslig and mes >= deslig:
            continue
        fat = fat or 0.0
        nivel, grat = _nivel_gratificacao(fat, params) if params else (None, 0.0)
        resultado.append({"nome": nome, "faturamento": fat, "nivel": nivel, "gratificacao": grat})

    # Profissionais com funcao correta mas sem movimento no mês
    nomes_com_fat = {r["nome"] for r in resultado}
    todos = con.execute(
        "SELECT nome_sistema FROM profissionais WHERE funcao=? ORDER BY nome_sistema",
        (funcao,),
    ).fetchall()
    for (nome,) in todos:
        if nome in nomes_com_fat:
            continue
        deslig = DESLIGAMENTOS.get(nome)
        if deslig and mes >= deslig:
            continue
        resultado.append({"nome": nome, "faturamento": 0.0, "nivel": None, "gratificacao": 0.0})

    return resultado


def _imprimir(mes: str, politica: str, linhas: list[dict]) -> None:
    print(f"\nApuração {politica} — {mes}")
    print(f"{'Nome':<45} {'Faturamento':>12}")
    print("-" * 60)
    total = 0.0
    for r in linhas:
        print(f"  {r['nome']:<43} R${r['faturamento']:>9,.2f}")
        total += r["faturamento"]
    print("-" * 60)
    print(f"  {'TOTAL':>43} R${total:>9,.2f}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Apura faturamento de manicures/assistentes.")
    parser.add_argument("mes", help="Mês no formato YYYY-MM")
    parser.add_argument("politica", choices=["manicures", "assistentes"])
    parser.add_argument("--seed", action="store_true", help="Executa seed de funções antes de apurar")
    args = parser.parse_args()

    if not os.path.exists(DB_PATH):
        print(f"Banco não encontrado: {DB_PATH}", file=sys.stderr)
        sys.exit(1)

    with sqlite3.connect(DB_PATH) as con:
        if args.seed:
            seed_funcoes(con)
            print("Seed de funções executado.")
        linhas = apurar_faturamento(args.mes, args.politica, con)

    _imprimir(args.mes, args.politica, linhas)


if __name__ == "__main__":
    main()
