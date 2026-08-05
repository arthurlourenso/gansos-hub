"""
src/apuracao_faturamento.py — Apuração de faturamento de manicures e assistentes.
RN-12 (manicures) e RN-13 (assistentes, Raynara desligada ago/26).
Uso: python src/apuracao_faturamento.py <YYYY-MM> <manicures|assistentes>
"""
import argparse
import os
import sqlite3
import sys

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "db", "gansos.db")

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

def apurar_faturamento(mes: str, politica: str, con: sqlite3.Connection) -> list[dict]:
    """
    Retorna faturamento de cada profissional da política no mês informado.
    politica: 'manicures' ou 'assistentes'
    mes: 'YYYY-MM'
    Aplica RN-13: exclui assistentes desligadas cujo desligamento seja <= mes.
    """
    funcao = _POLITICA_FUNCAO.get(politica)
    if not funcao:
        raise ValueError(f"Política inválida: {politica!r}. Use 'manicures' ou 'assistentes'.")

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
        resultado.append({"nome": nome, "faturamento": fat or 0.0})

    # Incluir profissionais com funcao correta mas sem movimento no mês (fat=0)
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
        resultado.append({"nome": nome, "faturamento": 0.0})

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
