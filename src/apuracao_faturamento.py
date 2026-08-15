"""
src/apuracao_faturamento.py — Apuração de faturamento de manicures, assistentes e recepção/caixa.
RN-12 (manicures, metas individualizadas a partir de ago/2026)
RN-13 (assistentes, prêmios atualizados ago/2026, Raynara desligada ago/26)
RN-14 (recepção/caixa: venda de produtos, vigência ago/2026)
Uso: python -m src.apuracao_faturamento <YYYY-MM> <manicures|assistentes|recepcao_caixa>
"""
import argparse
import os
import sys
from datetime import datetime

import src.db as db

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "db", "gansos.db")

_VIGENCIA_INICIO = "2026-01-01"
_VIGENCIA_AGOSTO = "2026-08-01"

# RN-12: manicures — parâmetros genéricos históricos (jan/2026, fallback para meses anteriores)
_PARAMS_MANICURES_HISTORICO = [
    ("bronze_meta",   "6000"),
    ("bronze_premio", "150"),
    ("prata_meta",    "8000"),
    ("prata_premio",  "200"),
    ("ouro_meta",    "10000"),
    ("ouro_premio",   "300"),
]

# RN-12: metas individualizadas por manicure (ago/2026)
_METAS_MANICURES_INDIVIDUAIS = {
    "Isaura Jéssica dos Santos Alves": [
        ("bronze_meta", "12300"), ("prata_meta", "13300"), ("ouro_meta", "14350"),
    ],
    "Esmeralda Belém dos Santos": [
        ("bronze_meta", "11650"), ("prata_meta", "12650"), ("ouro_meta", "13600"),
    ],
    "Rayssa Leite Da Silva Soares": [
        ("bronze_meta", "10150"), ("prata_meta", "11000"), ("ouro_meta", "11850"),
    ],
    "Safira Belém dos Santos": [
        ("bronze_meta", "7000"), ("prata_meta", "7600"), ("ouro_meta", "8150"),
    ],
}

# RN-12: prêmios gerais (ago/2026) — iguais para todas as manicures
_PREMIOS_MANICURES_AGOSTO = [
    ("bronze_premio", "150"),
    ("prata_premio",  "200"),
    ("ouro_premio",   "300"),
]

# RN-13: assistentes — vigência original (jan/2026)
_PARAMS_ASSISTENTES_ORIGINAL = [
    ("bronze_meta",  "2500"), ("bronze_premio", "100"),
    ("prata_meta",   "3500"), ("prata_premio",  "200"),
    ("ouro_meta",    "5000"), ("ouro_premio",   "350"),
]

# RN-13: assistentes — prêmios atualizados (ago/2026)
_PARAMS_ASSISTENTES_AGOSTO = [
    ("bronze_meta",  "2500"), ("bronze_premio", "150"),
    ("prata_meta",   "3500"), ("prata_premio",  "225"),
    ("ouro_meta",    "5000"), ("ouro_premio",   "300"),
]

# RN-14: recepção/caixa — venda de produtos (ago/2026)
_PARAMS_RECEPCAO = [
    ("bronze_meta",   "5000"), ("bronze_premio", "100"),
    ("prata_meta",    "7000"), ("prata_premio",  "175"),
    ("ouro_meta",     "8000"), ("ouro_premio",   "250"),
]

MANICURES = [
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

RECEPCAO_CAIXA = [
    "Thamires Ferreira",
    "Evelly Caroline Araujo de Sousa",
]

# RN-13: Raynara desligada a partir de ago/2026
DESLIGAMENTOS = {
    "Raynara de Cassia Cutrim Dos Santos": "2026-08",
}

_POLITICA_FUNCAO = {
    "manicures":   "manicure",
    "assistentes": "assistente",
}


# ---------------------------------------------------------------------------
# Seed
# ---------------------------------------------------------------------------

def seed_parametros(con) -> None:
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _ins(politica, chave, valor, vigencia, profissional=None):
        if profissional:
            existe = con.execute(
                "SELECT 1 FROM parametros WHERE politica=? AND chave=? AND vigencia_inicio=? AND profissional=?",
                (politica, chave, vigencia, profissional),
            ).fetchone()
        else:
            existe = con.execute(
                "SELECT 1 FROM parametros WHERE politica=? AND chave=? AND vigencia_inicio=? AND profissional IS NULL",
                (politica, chave, vigencia),
            ).fetchone()
        if not existe:
            con.execute(
                """INSERT INTO parametros
                   (politica, chave, valor, vigencia_inicio, vigencia_fim, profissional, alterado_por, alterado_em)
                   VALUES (?,?,?,?,NULL,?,'sistema',?)""",
                (politica, chave, valor, vigencia, profissional, agora),
            )

    # Manicures — histórico geral (jan/2026)
    for chave, valor in _PARAMS_MANICURES_HISTORICO:
        _ins("gratificacao_manicures", chave, valor, _VIGENCIA_INICIO)

    # Manicures — metas individuais (ago/2026)
    for nome, metas in _METAS_MANICURES_INDIVIDUAIS.items():
        for chave, valor in metas:
            _ins("gratificacao_manicures", chave, valor, _VIGENCIA_AGOSTO, profissional=nome)

    # Manicures — prêmios gerais atualizados (ago/2026)
    for chave, valor in _PREMIOS_MANICURES_AGOSTO:
        _ins("gratificacao_manicures", chave, valor, _VIGENCIA_AGOSTO)

    # Assistentes — original (jan/2026)
    for chave, valor in _PARAMS_ASSISTENTES_ORIGINAL:
        _ins("gratificacao_assistentes", chave, valor, _VIGENCIA_INICIO)

    # Assistentes — prêmios atualizados (ago/2026)
    for chave, valor in _PARAMS_ASSISTENTES_AGOSTO:
        _ins("gratificacao_assistentes", chave, valor, _VIGENCIA_AGOSTO)

    # Recepção/caixa (ago/2026)
    for chave, valor in _PARAMS_RECEPCAO:
        _ins("gratificacao_recepcao_caixa", chave, valor, _VIGENCIA_AGOSTO)

    con.commit()


def seed_funcoes(con) -> None:
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

def _get_params_fat(politica: str, mes: str, con, profissional: str | None = None) -> dict | None:
    """Parâmetros vigentes no mês para a política. Tenta profissional específico, cai para genérico."""
    nome_politica = f"gratificacao_{politica}"
    mes_inicio = mes + "-01"
    params: dict[str, str] = {}

    if profissional:
        rows = con.execute(
            """SELECT chave, valor FROM parametros
               WHERE politica = ? AND profissional = ?
                 AND vigencia_inicio <= ?
                 AND (vigencia_fim IS NULL OR vigencia_fim > ?)
               ORDER BY vigencia_inicio DESC""",
            (nome_politica, profissional, mes_inicio, mes_inicio),
        ).fetchall()
        for r in rows:
            params.setdefault(r["chave"], r["valor"])

    rows = con.execute(
        """SELECT chave, valor FROM parametros
           WHERE politica = ? AND profissional IS NULL
             AND vigencia_inicio <= ?
             AND (vigencia_fim IS NULL OR vigencia_fim > ?)
           ORDER BY vigencia_inicio DESC""",
        (nome_politica, mes_inicio, mes_inicio),
    ).fetchall()
    for r in rows:
        params.setdefault(r["chave"], r["valor"])

    return params if params else None


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


def apurar_faturamento(mes: str, politica: str, con) -> list[dict]:
    """
    Retorna faturamento de cada profissional da política no mês.
    politica: 'manicures' ou 'assistentes'
    Aplica RN-12/13 com lookup de parâmetros por profissional (com fallback genérico).
    """
    funcao = _POLITICA_FUNCAO.get(politica)
    if not funcao:
        raise ValueError(f"Política inválida: {politica!r}. Use 'manicures' ou 'assistentes'.")

    rows = con.execute(
        f"""SELECT p.nome_sistema, ROUND(SUM(v.valor), 2) as fat
           FROM vendas v
           JOIN profissionais p ON p.id = v.profissional_id
           WHERE p.funcao = ?
             AND v.tipo = 'Serviço'
             AND {db.mes_expr('v.data_hora')} = ?
           GROUP BY p.nome_sistema
           ORDER BY fat DESC""",
        (funcao, mes),
    ).fetchall()

    resultado = []
    nomes_com_fat: set[str] = set()
    for nome, fat in rows:
        deslig = DESLIGAMENTOS.get(nome)
        if deslig and mes >= deslig:
            continue
        fat = fat or 0.0
        nomes_com_fat.add(nome)
        params = _get_params_fat(politica, mes, con, profissional=nome)
        nivel, grat = _nivel_gratificacao(fat, params) if params else (None, 0.0)
        resultado.append({"nome": nome, "faturamento": fat, "nivel": nivel, "gratificacao": grat})

    todos = con.execute(
        "SELECT nome_sistema FROM profissionais WHERE funcao=? AND ativo=1 ORDER BY nome_sistema",
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


def apurar_recepcao_caixa(mes: str, con) -> list[dict]:
    """
    Apura recepção/caixa (RN-14): a meta é coletiva (total de produtos do setor),
    mas o prêmio é individual — cada pessoa ativa recebe se o setor bater a meta.
    Retorna vendas individuais + nível/prêmio baseados no total do setor.
    """
    params = _get_params_fat("recepcao_caixa", mes, con)

    # Total do setor para determinar o nível coletivo
    total_row = con.execute(
        f"""SELECT ROUND(SUM(v.valor), 2) as fat
           FROM vendas v
           JOIN profissionais p ON p.id = v.profissional_id
           WHERE p.funcao = 'recepcao_caixa'
             AND v.tipo = 'Produto'
             AND {db.mes_expr('v.data_hora')} = ?""",
        (mes,),
    ).fetchone()
    total_setor = total_row["fat"] or 0.0
    nivel, grat_individual = _nivel_gratificacao(total_setor, params) if params else (None, 0.0)

    # Vendas individuais (para exibição)
    rows = con.execute(
        f"""SELECT p.nome_sistema, ROUND(SUM(v.valor), 2) as fat
           FROM vendas v
           JOIN profissionais p ON p.id = v.profissional_id
           WHERE p.funcao = 'recepcao_caixa'
             AND v.tipo = 'Produto'
             AND {db.mes_expr('v.data_hora')} = ?
           GROUP BY p.nome_sistema""",
        (mes,),
    ).fetchall()
    fat_por_nome = {r["nome_sistema"]: (r["fat"] or 0.0) for r in rows}

    todos = con.execute(
        "SELECT nome_sistema FROM profissionais WHERE funcao='recepcao_caixa' AND ativo=1 ORDER BY nome_sistema"
    ).fetchall()

    return [
        {
            "nome": nome,
            "faturamento": fat_por_nome.get(nome, 0.0),
            "total_setor": total_setor,
            "nivel": nivel,
            "gratificacao": grat_individual,
        }
        for (nome,) in todos
    ]


def _imprimir(mes: str, politica: str, linhas: list[dict]) -> None:
    print(f"\nApuração {politica} — {mes}")
    print(f"{'Nome':<45} {'Faturamento':>12} {'Nível':<8} {'Grat':>8}")
    print("-" * 80)
    total = 0.0
    for r in linhas:
        print(f"  {r['nome']:<43} R${r['faturamento']:>9,.2f}  {r['nivel'] or '-':<8} R${r['gratificacao']:>6,.2f}")
        total += r["faturamento"]
    print("-" * 80)
    print(f"  {'TOTAL':>43} R${total:>9,.2f}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Apura faturamento de manicures/assistentes/recepção.")
    parser.add_argument("mes", help="Mês no formato YYYY-MM")
    parser.add_argument("politica", choices=["manicures", "assistentes", "recepcao_caixa"])
    parser.add_argument("--seed", action="store_true", help="Executa seed antes de apurar")
    args = parser.parse_args()

    if not os.path.exists(DB_PATH):
        print(f"Banco não encontrado: {DB_PATH}", file=sys.stderr)
        sys.exit(1)

    with db.conectar() as con:
        if args.seed:
            seed_funcoes(con)
            seed_parametros(con)
            print("Seed executado.")
        if args.politica == "recepcao_caixa":
            linhas = apurar_recepcao_caixa(args.mes, con)
        else:
            linhas = apurar_faturamento(args.mes, args.politica, con)

    _imprimir(args.mes, args.politica, linhas)


if __name__ == "__main__":
    main()
