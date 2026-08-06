"""
src/apuracao_barbeiros.py — Apuração de gratificação de barbeiros (RN-10).
Uso: python src/apuracao_barbeiros.py <YYYY-MM>
"""
import argparse
import os
import sys
from datetime import datetime

import src.db as db

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "db", "gansos.db")


# ---------------------------------------------------------------------------
# Seed
# ---------------------------------------------------------------------------

PARAMETROS_BARBEIROS = [
    ("bronze_meta",          "120"),
    ("bronze_premio",        "150"),
    ("prata_meta",           "135"),
    ("prata_premio",         "300"),
    ("ouro_meta",            "150"),
    ("ouro_premio",          "500"),
    ("minimo_atendimentos",  "50"),
]

# Cobre todo o período retroativo jan–jul/2026; revisão trimestral formal a partir de ago/2026
VIGENCIA_INICIO = "2026-01-01"

BARBEIROS = [
    "Mateus  Lima",
    "William Silva Melo",
    "Davi Silva Martins",
    "Caique Campos Ferreira",
    "Getúlio Silva Do Nascimento Junior",
    "Thiago Siqueira",
    "Ederson Duarte Carvalho",
    "Jose Erivelton Viana Leles",
    "Jose Jefferson Antonis Da Silva Junior",
    "Pedro Ian Ferreira De Souza",
    "Wellerson Victor Silva Sousa",
]


def seed_parametros(con) -> None:
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for chave, valor in PARAMETROS_BARBEIROS:
        existe = con.execute(
            "SELECT 1 FROM parametros WHERE politica=? AND chave=? AND vigencia_inicio=?",
            ("gratificacao_barbeiros", chave, VIGENCIA_INICIO),
        ).fetchone()
        if not existe:
            con.execute(
                """INSERT INTO parametros
                   (politica, chave, valor, vigencia_inicio, vigencia_fim, alterado_por, alterado_em)
                   VALUES (?, ?, ?, ?, NULL, 'sistema', ?)""",
                ("gratificacao_barbeiros", chave, valor, VIGENCIA_INICIO, agora),
            )
    con.commit()


def seed_funcoes(con) -> None:
    for nome in BARBEIROS:
        con.execute(
            "UPDATE profissionais SET funcao='barbeiro' WHERE nome_sistema=? AND funcao='pendente'",
            (nome,),
        )
    con.commit()


# ---------------------------------------------------------------------------
# Apuração
# ---------------------------------------------------------------------------

def _get_params(mes: str, con) -> dict:
    """Retorna parâmetros vigentes no mês (mais recente antes ou no mês)."""
    mes_inicio = mes + "-01"
    rows = con.execute(
        """SELECT chave, valor FROM parametros
           WHERE politica = 'gratificacao_barbeiros'
             AND vigencia_inicio <= ?
             AND (vigencia_fim IS NULL OR vigencia_fim > ?)
           ORDER BY vigencia_inicio DESC""",
        (mes_inicio, mes_inicio),
    ).fetchall()
    if not rows:
        raise ValueError(
            f"Nenhum parâmetro de gratificacao_barbeiros vigente em {mes}. "
            "Rode seed_parametros() antes."
        )
    # Em caso de múltiplas vigências sobrepostas, prioriza a mais recente por chave
    params: dict[str, str] = {}
    for chave, valor in rows:
        params.setdefault(chave, valor)
    return params


def apurar_barbeiros(mes: str, con) -> list[dict]:
    """
    Apura gratificação de barbeiros para o mês informado (RN-10).
    mes: 'YYYY-MM'
    Retorna: lista de dicts com nome, atendimentos, receita, ticket_medio,
             elegivel, nivel, gratificacao.
    """
    params = _get_params(mes, con)
    min_atend  = int(params["minimo_atendimentos"])
    niveis = [
        ("Ouro",   float(params["ouro_meta"]),   float(params["ouro_premio"])),
        ("Prata",  float(params["prata_meta"]),  float(params["prata_premio"])),
        ("Bronze", float(params["bronze_meta"]), float(params["bronze_premio"])),
    ]

    # Pendentes com vendas de serviço no mês → aviso
    pendentes = con.execute(
        f"""SELECT DISTINCT p.nome_sistema
           FROM vendas v JOIN profissionais p ON p.id = v.profissional_id
           WHERE p.funcao = 'pendente' AND v.tipo = 'Serviço'
             AND {db.mes_expr('v.data_hora')} = ?""",
        (mes,),
    ).fetchall()
    if pendentes:
        nomes = ", ".join(r[0] for r in pendentes)
        print(f"[AVISO] Profissionais 'pendente' com serviços em {mes} (ignorados): {nomes}",
              file=sys.stderr)

    rows = con.execute(
        f"""SELECT p.nome_sistema,
                  COUNT(DISTINCT {db.date_expr('v.data_hora')} || '|' || v.cliente) AS atend,
                  SUM(v.valor) AS receita
           FROM vendas v
           JOIN profissionais p ON p.id = v.profissional_id
           WHERE p.funcao = 'barbeiro'
             AND v.tipo = 'Serviço'
             AND {db.mes_expr('v.data_hora')} = ?
             AND v.cliente IS NOT NULL AND v.cliente != ''
           GROUP BY p.nome_sistema
           ORDER BY p.nome_sistema""",
        (mes,),
    ).fetchall()

    resultado = []
    for nome, atend, receita in rows:
        tm = round(receita / atend, 2) if atend else 0.0
        elegivel = atend >= min_atend
        nivel = None
        gratificacao = 0.0
        if elegivel:
            for n, meta, premio in niveis:
                if tm >= meta:
                    nivel = n
                    gratificacao = premio
                    break
        resultado.append({
            "nome": nome,
            "atendimentos": atend,
            "receita": receita,
            "ticket_medio": tm,
            "elegivel": elegivel,
            "nivel": nivel,
            "gratificacao": gratificacao,
        })

    return resultado


def _imprimir(mes: str, linhas: list[dict]) -> None:
    print(f"\nApuração barbeiros — {mes}")
    print(f"{'Nome':<45} {'Atend':>6} {'Receita':>11} {'TM':>8}  {'Nível':<8} {'Grat':>7}")
    print("-" * 96)
    total_grat = 0.0
    for r in linhas:
        elig = "" if r["elegivel"] else " (inelig.)"
        nivel = (r["nivel"] or "-") + elig
        print(f"  {r['nome']:<43} {r['atendimentos']:>6} "
              f"R${r['receita']:>9,.2f} {r['ticket_medio']:>8.2f}  {nivel:<18} R${r['gratificacao']:>6,.2f}")
        total_grat += r["gratificacao"]
    print("-" * 96)
    print(f"  {'TOTAL':>69} R${total_grat:>6,.2f}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Apura gratificação de barbeiros (RN-10).")
    parser.add_argument("mes", help="Mês no formato YYYY-MM")
    parser.add_argument("--seed", action="store_true", help="Executa seed de parâmetros e funções antes de apurar")
    args = parser.parse_args()

    if not os.path.exists(DB_PATH):
        print(f"Banco não encontrado: {DB_PATH}", file=sys.stderr)
        sys.exit(1)

    with db.conectar() as con:
        if args.seed:
            seed_parametros(con)
            seed_funcoes(con)
            print("Seed executado.")
        linhas = apurar_barbeiros(args.mes, con)

    if not linhas:
        print(f"Nenhum barbeiro com serviços em {args.mes}.")
        return
    _imprimir(args.mes, linhas)


if __name__ == "__main__":
    main()
