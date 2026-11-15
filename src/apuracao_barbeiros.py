"""
src/apuracao_barbeiros.py — Apuração de gratificação de barbeiros (RN-10).
Uso: python src/apuracao_barbeiros.py <YYYY-MM>

RN-10 v1 (até ago/2026): TM mensal contra metas absolutas + mínimo de atendimentos.
RN-10 v2 (a partir de set/2026, parâmetro modelo=setor_tm): gate coletivo do setor +
TM individual; nível efetivo = menor entre o nível do setor e o do TM.
"""
import argparse
import math
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

# RN-10 v2: o nível efetivo de cada barbeiro é o MENOR entre o nível do setor
# (faturamento coletivo vs. média dos 3 meses anteriores) e o nível do seu TM
# (vs. a média do próprio TM nos 6 meses anteriores). Atendimento é só PDI.
VIGENCIA_V2 = "2026-09-01"
PARAMETROS_BARBEIROS_V2 = [
    ("modelo",                "setor_tm"),
    ("setor_base_meses",      "3"),
    ("setor_bronze_pct",      "0.07"),
    ("setor_prata_pct",       "0.12"),
    ("setor_ouro_pct",        "0.18"),
    ("tm_baseline_meses",     "6"),
    ("tm_baseline_min_meses", "3"),
    ("tm_bronze_pct",         "0.07"),
    ("tm_prata_pct",          "0.12"),
    ("tm_ouro_pct",           "0.18"),
    ("bronze_premio",         "150"),
    ("prata_premio",          "300"),
    ("ouro_premio",           "500"),
    ("minimo_atendimentos",   "0"),
    ("pdi_atend_pct",         "0.10"),
    ("excluidos",             "Getúlio Silva Do Nascimento Junior"),
    # "A>B|C>D": A usa o histórico (baseline de TM e atendimentos) de B
    ("baseline_como",         "Pedro Ian Ferreira De Souza>William Silva Melo"),
]

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
    "Andre Lucas",
    "Yasmin Abreu Soares",
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
    seed_parametros_v2(con)


def seed_parametros_v2(con) -> None:
    """Abre a vigência RN-10 v2 em 2026-09-01 e fecha a anterior (meses antigos não mudam)."""
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    con.execute(
        """UPDATE parametros SET vigencia_fim = ?
           WHERE politica = 'gratificacao_barbeiros' AND profissional IS NULL
             AND vigencia_fim IS NULL AND vigencia_inicio < ?""",
        (VIGENCIA_V2, VIGENCIA_V2),
    )
    for chave, valor in PARAMETROS_BARBEIROS_V2:
        existe = con.execute(
            "SELECT 1 FROM parametros WHERE politica=? AND chave=? AND vigencia_inicio=?",
            ("gratificacao_barbeiros", chave, VIGENCIA_V2),
        ).fetchone()
        if not existe:
            con.execute(
                """INSERT INTO parametros
                   (politica, chave, valor, vigencia_inicio, vigencia_fim, alterado_por, alterado_em)
                   VALUES (?, ?, ?, ?, NULL, 'sistema', ?)""",
                ("gratificacao_barbeiros", chave, valor, VIGENCIA_V2, agora),
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

_NIVEIS = ["Bronze", "Prata", "Ouro"]


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


def _meses_anteriores(mes: str, n: int) -> list[str]:
    """Os n meses antes de `mes`, do mais recente para o mais antigo."""
    ano, m = int(mes[:4]), int(mes[5:7])
    out = []
    for _ in range(n):
        m -= 1
        if m == 0:
            ano, m = ano - 1, 12
        out.append(f"{ano:04d}-{m:02d}")
    return out


def _stats_mes(mes: str, con) -> dict[str, tuple[int, float]]:
    """{nome: (atendimentos, receita)} de serviços por barbeiro no mês."""
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
    return {nome: (atend, receita) for nome, atend, receita in rows}


def _excluidos(params: dict) -> set[str]:
    return {n for n in params.get("excluidos", "").split("|") if n}


def _baseline_como(params: dict) -> dict[str, str]:
    pares = (p.split(">") for p in params.get("baseline_como", "").split("|") if ">" in p)
    return {a.strip(): b.strip() for a, b in pares}


def _contexto_setor(mes: str, params: dict, con) -> dict:
    """Faturamento do setor no mês contra a base (média dos N meses anteriores)."""
    excl = _excluidos(params)
    n_base = int(params["setor_base_meses"])

    def fat(m):
        return sum(r for n, (_, r) in _stats_mes(m, con).items() if n not in excl)

    fats = [f for f in (fat(m) for m in _meses_anteriores(mes, n_base)) if f > 0]
    base = round(sum(fats) / len(fats), 2) if fats else None
    atual = round(fat(mes), 2)
    metas = {}
    nivel = None
    if base:
        for n in _NIVEIS:
            metas[n] = round(base * (1 + float(params[f"setor_{n.lower()}_pct"])), 2)
            if atual >= metas[n]:
                nivel = n
    return {
        "faturamento": atual,
        "base": base,
        "variacao_pct": round((atual / base - 1) * 100, 1) if base else None,
        "metas": metas,
        "nivel": nivel,
    }


def resumo_setor(mes: str, con) -> dict | None:
    """Gate coletivo do setor no mês; None para meses ainda na régua v1."""
    params = _get_params(mes, con)
    if params.get("modelo") != "setor_tm":
        return None
    return _contexto_setor(mes, params, con)


def _apurar_setor_tm(mes: str, params: dict, atual: dict, con) -> list[dict]:
    """RN-10 v2: nível efetivo = min(nível do setor, nível do TM individual)."""
    excl = _excluidos(params)
    setor = _contexto_setor(mes, params, con)
    n_hist = int(params["tm_baseline_meses"])
    min_hist = int(params["tm_baseline_min_meses"])
    min_atend = int(params["minimo_atendimentos"])
    pdi_pct = float(params["pdi_atend_pct"])
    historico = [_stats_mes(m, con) for m in _meses_anteriores(mes, n_hist)]
    # Suporte a base de TM individual configurada diretamente no banco
    base_fixa_rows = con.execute(
        """SELECT profissional, valor FROM parametros
           WHERE politica = 'gratificacao_barbeiros' AND chave = 'tm_base_fixa'
             AND profissional IS NOT NULL
             AND vigencia_inicio <= ?
             AND (vigencia_fim IS NULL OR vigencia_fim > ?)
           ORDER BY vigencia_inicio DESC""",
        (mes + "-01", mes + "-01"),
    ).fetchall()
    bases_fixas = {r["profissional"]: float(r["valor"]) for r in base_fixa_rows}
    como = _baseline_como(params)

    resultado = []
    for nome, (atend, receita) in atual.items():
        if nome in excl:
            continue
        tm = round(receita / atend, 2) if atend else 0.0

        if nome in bases_fixas:
            tm_base = round(bases_fixas[nome], 2)
            tem_base = True
            ref = "base fixa (William)"
            tms_count = n_hist
            atend_base = atend
        else:
            ref = como.get(nome)
            fonte = ref or nome
            tms, atends = [], []
            for h in historico:
                if fonte in h and h[fonte][0]:
                    tms.append(round(h[fonte][1] / h[fonte][0], 2))
                    atends.append(h[fonte][0])
            tem_base = len(tms) >= min_hist
            tm_base = round(sum(tms) / len(tms), 2) if tem_base else None
            atend_base = sum(atends) / len(atends) if tem_base else None
            tms_count = len(tms)

        pisos = {}
        nivel_tm = None
        if tem_base:
            for n in _NIVEIS:
                pisos[n] = round(tm_base * (1 + float(params[f"tm_{n.lower()}_pct"])), 2)
                if tm >= pisos[n]:
                    nivel_tm = n

        elegivel = atend >= min_atend
        nivel = None
        if elegivel and setor["nivel"] and nivel_tm:
            nivel = _NIVEIS[min(_NIVEIS.index(setor["nivel"]), _NIVEIS.index(nivel_tm))]
        gratificacao = float(params[f"{nivel.lower()}_premio"]) if nivel else 0.0

        pdi_meta = math.ceil(round(atend_base * (1 + pdi_pct), 6)) if tem_base else None
        resultado.append({
            "nome": nome,
            "atendimentos": atend,
            "receita": receita,
            "ticket_medio": tm,
            "elegivel": elegivel,
            "nivel": nivel,
            "gratificacao": gratificacao,
            "modelo": "setor_tm",
            "nivel_setor": setor["nivel"],
            "nivel_tm": nivel_tm,
            "tm_base": tm_base,
            "baseline_meses": tms_count,
            "baseline_ref": ref,
            "piso_bronze": pisos.get("Bronze"),
            "piso_prata": pisos.get("Prata"),
            "piso_ouro": pisos.get("Ouro"),
            "pdi_meta": pdi_meta,
            "pdi_atingiu": (atend >= pdi_meta) if pdi_meta is not None else None,
        })
    return resultado


def _apurar_legado(params: dict, atual: dict) -> list[dict]:
    """RN-10 v1: TM mensal contra metas absolutas, com mínimo de atendimentos."""
    min_atend = int(params["minimo_atendimentos"])
    niveis = [
        ("Ouro",   float(params["ouro_meta"]),   float(params["ouro_premio"])),
        ("Prata",  float(params["prata_meta"]),  float(params["prata_premio"])),
        ("Bronze", float(params["bronze_meta"]), float(params["bronze_premio"])),
    ]
    resultado = []
    for nome, (atend, receita) in atual.items():
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
            "modelo": "legado",
        })
    return resultado


def apurar_barbeiros(mes: str, con) -> list[dict]:
    """
    Apura gratificação de barbeiros para o mês informado (RN-10).
    mes: 'YYYY-MM'
    Retorna: lista de dicts com nome, atendimentos, receita, ticket_medio,
             elegivel, nivel (efetivo), gratificacao e modelo ('legado' | 'setor_tm').
    """
    params = _get_params(mes, con)

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

    atual = _stats_mes(mes, con)
    if params.get("modelo") == "setor_tm":
        return _apurar_setor_tm(mes, params, atual, con)
    return _apurar_legado(params, atual)


def _imprimir(mes: str, linhas: list[dict], setor: dict | None = None) -> None:
    print(f"\nApuração barbeiros — {mes}")
    if setor:
        print(f"Setor: R${setor['faturamento']:,.2f} vs base R${setor['base']:,.2f} "
              f"({setor['variacao_pct']:+.1f}%) - nível do setor: {setor['nivel'] or 'nenhum'}")
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
        setor = resumo_setor(args.mes, con)

    if not linhas:
        print(f"Nenhum barbeiro com serviços em {args.mes}.")
        return
    _imprimir(args.mes, linhas, setor)


if __name__ == "__main__":
    main()
