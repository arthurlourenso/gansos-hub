"""
src/dashboard.py — Dashboard Gansos Hub.
Uso: streamlit run src/dashboard.py
"""
import os
import sqlite3

import pandas as pd
import streamlit as st

ROOT_DIR = os.path.join(os.path.dirname(__file__), "..")
DB_PATH = os.path.join(ROOT_DIR, "db", "gansos.db")

st.set_page_config(
    page_title="Gansos Hub",
    page_icon="✂️",
    layout="wide",
)


# ---------------------------------------------------------------------------
# Utilitários
# ---------------------------------------------------------------------------

@st.cache_resource
def _conectar():
    con = sqlite3.connect(DB_PATH, check_same_thread=False)
    con.row_factory = sqlite3.Row
    return con


def _con():
    return _conectar()


def _meses_disponiveis(con) -> list[str]:
    rows = con.execute(
        "SELECT DISTINCT strftime('%Y-%m', data_hora) as mes FROM vendas ORDER BY mes DESC"
    ).fetchall()
    return [r[0] for r in rows]


def _fmt_brl(v: float) -> str:
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _nivel_badge(nivel: str | None) -> str:
    cores = {"Bronze": "🟤", "Prata": "⚪", "Ouro": "🟡"}
    return f"{cores.get(nivel, '')} {nivel}" if nivel else "—"


# ---------------------------------------------------------------------------
# Aba 1 — Vendas
# ---------------------------------------------------------------------------

def _tab_vendas(con, mes: str):
    st.subheader(f"Receita — {mes}")

    rows = con.execute(
        """SELECT tipo,
                  ROUND(SUM(valor), 2) as total,
                  COUNT(*) as qtd
           FROM vendas
           WHERE strftime('%Y-%m', data_hora) = ?
           GROUP BY tipo""",
        (mes,),
    ).fetchall()

    total_mes = sum(r["total"] for r in rows)
    c1, c2, c3 = st.columns(3)
    for r in rows:
        col = c1 if r["tipo"] == "Serviço" else c2
        col.metric(r["tipo"], _fmt_brl(r["total"]), f"{r['qtd']} lançamentos")
    c3.metric("Total geral", _fmt_brl(total_mes))

    st.divider()

    # Comparativo mensal
    st.markdown("#### Receita mensal — todos os meses")
    hist = con.execute(
        """SELECT strftime('%Y-%m', data_hora) as mes,
                  tipo,
                  ROUND(SUM(valor), 2) as total
           FROM vendas
           GROUP BY mes, tipo
           ORDER BY mes""",
    ).fetchall()
    df_hist = pd.DataFrame([dict(r) for r in hist])
    if not df_hist.empty:
        df_pivot = df_hist.pivot(index="mes", columns="tipo", values="total").fillna(0)
        st.bar_chart(df_pivot, color=["#4e8cff", "#ff6b6b"])

    st.divider()

    # Top profissionais no mês
    st.markdown("#### Receita por profissional no mês")
    prof_rows = con.execute(
        """SELECT p.nome_sistema as profissional,
                  v.tipo,
                  ROUND(SUM(v.valor), 2) as total
           FROM vendas v
           JOIN profissionais p ON p.id = v.profissional_id
           WHERE strftime('%Y-%m', v.data_hora) = ?
           GROUP BY p.nome_sistema, v.tipo
           ORDER BY total DESC""",
        (mes,),
    ).fetchall()
    if prof_rows:
        df_prof = pd.DataFrame([dict(r) for r in prof_rows])
        df_prof["total"] = df_prof["total"].map(lambda v: f"R$ {v:,.2f}")
        st.dataframe(df_prof, width="stretch", hide_index=True)


# ---------------------------------------------------------------------------
# Aba 2 — Barbeiros
# ---------------------------------------------------------------------------

def _tab_barbeiros(con, mes: str):
    st.subheader(f"Barbeiros — {mes}")

    from src.apuracao_barbeiros import apurar_barbeiros
    try:
        linhas = apurar_barbeiros(mes, con)
    except ValueError as e:
        st.warning(str(e))
        return

    if not linhas:
        st.info("Nenhum barbeiro com serviços neste mês.")
        return

    df = pd.DataFrame(linhas)
    df["elegivel"] = df["elegivel"].map({True: "✓", False: "✗"})
    df["nivel"] = df["nivel"].apply(_nivel_badge)
    df["ticket_medio_fmt"] = df["ticket_medio"].map(_fmt_brl)
    df["receita_fmt"] = df["receita"].map(_fmt_brl)
    df["gratificacao_fmt"] = df["gratificacao"].map(_fmt_brl)

    st.dataframe(
        df[["nome", "atendimentos", "receita_fmt", "ticket_medio_fmt", "elegivel", "nivel", "gratificacao_fmt"]].rename(columns={
            "nome": "Profissional",
            "atendimentos": "Atend.",
            "receita_fmt": "Receita",
            "ticket_medio_fmt": "Ticket Médio",
            "elegivel": "Elig.",
            "nivel": "Nível",
            "gratificacao_fmt": "Gratificação",
        }),
        width="stretch",
        hide_index=True,
    )

    # Gráfico ticket médio × metas
    st.markdown("#### Ticket Médio × Metas")
    params_rows = con.execute(
        """SELECT chave, valor FROM parametros
           WHERE politica='gratificacao_barbeiros'
             AND vigencia_inicio <= ?
             AND (vigencia_fim IS NULL OR vigencia_fim > ?)
           ORDER BY vigencia_inicio DESC""",
        (mes + "-01", mes + "-01"),
    ).fetchall()
    params = {}
    for r in params_rows:
        params.setdefault(r["chave"], float(r["valor"]))

    df_chart = pd.DataFrame(linhas)[["nome", "ticket_medio"]].set_index("nome")
    st.bar_chart(df_chart)
    if params:
        st.caption(
            f"Metas: Bronze ≥ {_fmt_brl(params.get('bronze_meta', 120))} · "
            f"Prata ≥ {_fmt_brl(params.get('prata_meta', 135))} · "
            f"Ouro ≥ {_fmt_brl(params.get('ouro_meta', 150))}"
        )

    # Histórico
    st.markdown("#### Evolução histórica — ticket médio")
    meses_hist = con.execute(
        """SELECT DISTINCT strftime('%Y-%m', data_hora) as mes FROM vendas
           WHERE tipo='Serviço' ORDER BY mes""",
    ).fetchall()
    hist_data = []
    for (m,) in meses_hist:
        try:
            for r in apurar_barbeiros(m, con):
                hist_data.append({"mes": m, "nome": r["nome"], "ticket_medio": r["ticket_medio"]})
        except Exception:
            pass
    if hist_data:
        df_hist = pd.DataFrame(hist_data)
        df_pivot = df_hist.pivot(index="mes", columns="nome", values="ticket_medio").fillna(0)
        st.line_chart(df_pivot)


# ---------------------------------------------------------------------------
# Aba 3 — Apuração
# ---------------------------------------------------------------------------

def _tab_apuracao(con, mes: str):
    st.subheader(f"Apuração do mês — {mes}")

    from src.apuracao_barbeiros import apurar_barbeiros
    from src.apuracao_faturamento import apurar_faturamento

    total_grat = 0.0

    # Barbeiros
    st.markdown("#### Barbeiros")
    try:
        barb = apurar_barbeiros(mes, con)
        if barb:
            df_b = pd.DataFrame(barb)
            df_b = df_b[df_b["elegivel"]]
            if not df_b.empty:
                df_b["nivel"] = df_b["nivel"].apply(_nivel_badge)
                df_b["gratificacao"] = df_b["gratificacao"].map(_fmt_brl)
                st.dataframe(
                    df_b[["nome", "atendimentos", "ticket_medio", "nivel", "gratificacao"]].rename(columns={
                        "nome": "Barbeiro", "atendimentos": "Atend.",
                        "ticket_medio": "TM (R$)", "nivel": "Nível", "gratificacao": "Gratificação",
                    }),
                    width="stretch", hide_index=True,
                )
                grat_barb = sum(r["gratificacao"] for r in barb)
                total_grat += grat_barb
                st.caption(f"Subtotal barbeiros: {_fmt_brl(grat_barb)}")
            else:
                st.info("Nenhum barbeiro elegível neste mês.")
        else:
            st.info("Nenhum barbeiro com serviços neste mês.")
    except ValueError as e:
        st.warning(str(e))

    # Manicures
    st.markdown("#### Manicures")
    manic = apurar_faturamento(mes, "manicures", con)
    if manic:
        df_m = pd.DataFrame(manic)
        df_m["nivel"] = df_m["nivel"].apply(_nivel_badge)
        df_m["faturamento"] = df_m["faturamento"].map(_fmt_brl)
        df_m["gratificacao"] = df_m["gratificacao"].map(_fmt_brl)
        st.dataframe(
            df_m[["nome", "faturamento", "nivel", "gratificacao"]].rename(columns={
                "nome": "Manicure", "faturamento": "Faturamento",
                "nivel": "Nível", "gratificacao": "Gratificação",
            }),
            width="stretch", hide_index=True,
        )
        grat_m = sum(r["gratificacao"] for r in manic)
        total_grat += grat_m
        st.caption(f"Subtotal manicures: {_fmt_brl(grat_m)}")

    # Assistentes
    st.markdown("#### Assistentes")
    assist = apurar_faturamento(mes, "assistentes", con)
    if assist:
        df_a = pd.DataFrame(assist)
        df_a["nivel"] = df_a["nivel"].apply(_nivel_badge)
        df_a["faturamento"] = df_a["faturamento"].map(_fmt_brl)
        df_a["gratificacao"] = df_a["gratificacao"].map(_fmt_brl)
        st.dataframe(
            df_a[["nome", "faturamento", "nivel", "gratificacao"]].rename(columns={
                "nome": "Assistente", "faturamento": "Faturamento",
                "nivel": "Nível", "gratificacao": "Gratificação",
            }),
            width="stretch", hide_index=True,
        )
        grat_a = sum(r["gratificacao"] for r in assist)
        total_grat += grat_a
        st.caption(f"Subtotal assistentes: {_fmt_brl(grat_a)}")

    st.divider()
    st.metric("💰 Custo total de gratificações", _fmt_brl(total_grat))
    st.info("Publicação de apuração disponível no próximo ciclo (T7).")


# ---------------------------------------------------------------------------
# Aba 4 — Parâmetros
# ---------------------------------------------------------------------------

def _tab_parametros(con):
    st.subheader("Parâmetros vigentes")
    st.info("Edição com vigência disponível no próximo ciclo (T7).")

    rows = con.execute(
        """SELECT politica, chave, valor, vigencia_inicio, vigencia_fim, alterado_por, alterado_em
           FROM parametros
           ORDER BY politica, vigencia_inicio DESC, chave"""
    ).fetchall()

    if not rows:
        st.warning("Nenhum parâmetro cadastrado.")
        return

    df = pd.DataFrame([dict(r) for r in rows])
    df["vigencia_fim"] = df["vigencia_fim"].fillna("aberto")
    df.columns = ["Política", "Chave", "Valor", "Vigência Início", "Vigência Fim", "Alterado Por", "Alterado Em"]
    st.dataframe(df, width="stretch", hide_index=True)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if not os.path.exists(DB_PATH):
        st.error(f"Banco não encontrado: {DB_PATH}\n\nRode: `python init_db.py` e depois importe os arquivos.")
        return

    con = _con()
    meses = _meses_disponiveis(con)

    if not meses:
        st.warning("Nenhum dado importado. Rode `python src/ingestao.py <arquivo.xlsx>`.")
        return

    st.title("✂️ Gansos Hub")

    with st.sidebar:
        st.header("Filtros")
        mes_sel = st.selectbox("Mês", meses, index=0)

    t1, t2, t3, t4 = st.tabs(["📊 Vendas", "💈 Barbeiros", "📋 Apuração", "⚙️ Parâmetros"])

    with t1:
        _tab_vendas(con, mes_sel)
    with t2:
        _tab_barbeiros(con, mes_sel)
    with t3:
        _tab_apuracao(con, mes_sel)
    with t4:
        _tab_parametros(con)


if __name__ == "__main__":
    main()
