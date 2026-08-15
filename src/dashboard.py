"""
src/dashboard.py — Dashboard Gansos Hub.
Uso: streamlit run src/dashboard.py
"""
import os

import pandas as pd
import streamlit as st

import src.db as db

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
    return db.conectar()


def _con():
    return _conectar()


def _meses_disponiveis(con) -> list[str]:
    rows = con.execute(
        f"SELECT DISTINCT {db.mes_expr('data_hora')} as mes FROM vendas ORDER BY mes DESC"
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
        f"""SELECT tipo,
                  ROUND(SUM(valor), 2) as total,
                  COUNT(*) as qtd
           FROM vendas
           WHERE {db.mes_expr('data_hora')} = ?
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
        f"""SELECT {db.mes_expr('data_hora')} as mes,
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
        f"""SELECT p.nome_sistema as profissional,
                  v.tipo,
                  ROUND(SUM(v.valor), 2) as total
           FROM vendas v
           JOIN profissionais p ON p.id = v.profissional_id
           WHERE {db.mes_expr('v.data_hora')} = ?
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
        f"""SELECT DISTINCT {db.mes_expr('data_hora')} as mes FROM vendas
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
# Helpers de publicação (RN-21)
# ---------------------------------------------------------------------------

def _apuracao_publicada(con, mes: str, politica: str) -> dict | None:
    """Retorna o payload publicado se existir, None caso contrário."""
    import json
    row = con.execute(
        "SELECT payload_json, publicada_em FROM apuracoes WHERE mes=? AND politica=?",
        (mes, politica),
    ).fetchone()
    if row:
        return {"payload": json.loads(row["payload_json"]), "publicada_em": row["publicada_em"]}
    return None


def _publicar(con, mes: str, politica: str, linhas: list[dict]) -> None:
    import json
    from datetime import datetime
    payload = json.dumps(linhas, ensure_ascii=False)
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    con.execute(
        "INSERT INTO apuracoes (mes, politica, payload_json, publicada_em) VALUES (?,?,?,?)",
        (mes, politica, payload, agora),
    )
    con.commit()


def _bloco_apuracao(con, mes: str, politica: str, label: str, linhas: list[dict],
                    col_extra: list[str], rename: dict) -> float:
    """Renderiza bloco de apuração com botão publicar / badge publicado."""
    pub = _apuracao_publicada(con, mes, politica)

    if pub:
        st.success(f"✅ Publicada em {pub['publicada_em']} — exibindo snapshot imutável.")
        linhas_exib = pub["payload"]
    else:
        linhas_exib = linhas

    df = pd.DataFrame(linhas_exib)
    if df.empty:
        st.info(f"Nenhum(a) {label.lower()} com movimento neste mês.")
        return 0.0

    if "nivel" in df.columns:
        df["nivel"] = df["nivel"].apply(_nivel_badge)
    for col in ["faturamento", "gratificacao", "receita"]:
        if col in df.columns:
            df[col] = df[col].map(_fmt_brl)
    if "ticket_medio" in df.columns:
        df["ticket_medio"] = df["ticket_medio"].map(lambda v: f"R$ {v:.2f}")
    if "elegivel" in df.columns:
        df = df[df["elegivel"].astype(str).isin(["True", "true", True])]

    cols_show = [c for c in col_extra if c in df.columns]
    st.dataframe(df[cols_show].rename(columns=rename), width="stretch", hide_index=True)

    grat = sum(r.get("gratificacao", 0) for r in linhas_exib)
    st.caption(f"Subtotal {label.lower()}: {_fmt_brl(grat)}")

    if not pub:
        if st.button(f"Publicar apuração — {label} {mes}", key=f"pub_{politica}_{mes}"):
            _publicar(con, mes, politica, linhas)
            st.success("Apuração publicada! Recarregue para ver o badge.")
            st.rerun()

    return grat


# ---------------------------------------------------------------------------
# Aba 3 — Apuração
# ---------------------------------------------------------------------------

def _tab_apuracao(con, mes: str):
    st.subheader(f"Apuração do mês — {mes}")

    from src.apuracao_barbeiros import apurar_barbeiros
    from src.apuracao_faturamento import apurar_faturamento, apurar_recepcao_caixa

    total_grat = 0.0

    st.markdown("#### Barbeiros")
    try:
        barb = apurar_barbeiros(mes, con)
    except ValueError as e:
        st.warning(str(e))
        barb = []

    total_grat += _bloco_apuracao(
        con, mes, "barbeiros", "Barbeiros", barb,
        col_extra=["nome", "atendimentos", "ticket_medio", "nivel", "gratificacao"],
        rename={"nome": "Barbeiro", "atendimentos": "Atend.", "ticket_medio": "TM (R$)",
                "nivel": "Nível", "gratificacao": "Gratificação"},
    )

    st.markdown("#### Manicures")
    manic = apurar_faturamento(mes, "manicures", con)
    total_grat += _bloco_apuracao(
        con, mes, "manicures", "Manicures", manic,
        col_extra=["nome", "faturamento", "nivel", "gratificacao"],
        rename={"nome": "Manicure", "faturamento": "Faturamento",
                "nivel": "Nível", "gratificacao": "Gratificação"},
    )

    st.markdown("#### Assistentes")
    assist = apurar_faturamento(mes, "assistentes", con)
    total_grat += _bloco_apuracao(
        con, mes, "assistentes", "Assistentes", assist,
        col_extra=["nome", "faturamento", "nivel", "gratificacao"],
        rename={"nome": "Assistente", "faturamento": "Faturamento",
                "nivel": "Nível", "gratificacao": "Gratificação"},
    )

    st.markdown("#### Recepção / Caixa")
    recep = apurar_recepcao_caixa(mes, con)
    total_grat += _bloco_apuracao(
        con, mes, "recepcao_caixa", "Recepção/Caixa", recep,
        col_extra=["nome", "faturamento", "nivel", "gratificacao"],
        rename={"nome": "Profissional", "faturamento": "Venda Produtos",
                "nivel": "Nível", "gratificacao": "Gratificação"},
    )

    st.divider()
    st.metric("💰 Custo total de gratificações", _fmt_brl(total_grat))


# ---------------------------------------------------------------------------
# Aba 4 — Parâmetros (edição com vigência — RN-20)
# ---------------------------------------------------------------------------

_POLITICAS_CAMPOS = {
    "gratificacao_barbeiros": {
        "label": "Barbeiros",
        "campos": [
            ("bronze_meta",         "Bronze — Meta TM (R$)"),
            ("bronze_premio",       "Bronze — Prêmio (R$)"),
            ("prata_meta",          "Prata — Meta TM (R$)"),
            ("prata_premio",        "Prata — Prêmio (R$)"),
            ("ouro_meta",           "Ouro — Meta TM (R$)"),
            ("ouro_premio",         "Ouro — Prêmio (R$)"),
            ("minimo_atendimentos", "Mínimo de atendimentos"),
        ],
    },
    "gratificacao_manicures": {
        "label": "Manicures",
        "campos": [
            ("bronze_meta",   "Bronze — Meta fat. (R$)"),
            ("bronze_premio", "Bronze — Prêmio (R$)"),
            ("prata_meta",    "Prata — Meta fat. (R$)"),
            ("prata_premio",  "Prata — Prêmio (R$)"),
            ("ouro_meta",     "Ouro — Meta fat. (R$)"),
            ("ouro_premio",   "Ouro — Prêmio (R$)"),
        ],
    },
    "gratificacao_assistentes": {
        "label": "Assistentes",
        "campos": [
            ("bronze_meta",   "Bronze — Meta fat. (R$)"),
            ("bronze_premio", "Bronze — Prêmio (R$)"),
            ("prata_meta",    "Prata — Meta fat. (R$)"),
            ("prata_premio",  "Prata — Prêmio (R$)"),
            ("ouro_meta",     "Ouro — Meta fat. (R$)"),
            ("ouro_premio",   "Ouro — Prêmio (R$)"),
        ],
    },
    "gratificacao_recepcao_caixa": {
        "label": "Recepção / Caixa (produtos)",
        "campos": [
            ("bronze_meta",   "Bronze — Meta produtos (R$)"),
            ("bronze_premio", "Bronze — Prêmio (R$)"),
            ("prata_meta",    "Prata — Meta produtos (R$)"),
            ("prata_premio",  "Prata — Prêmio (R$)"),
            ("ouro_meta",     "Ouro — Meta produtos (R$)"),
            ("ouro_premio",   "Ouro — Prêmio (R$)"),
        ],
    },
}


def _params_vigentes(con, politica: str, mes_inicio: str) -> dict[str, str]:
    rows = con.execute(
        """SELECT chave, valor FROM parametros
           WHERE politica=?
             AND profissional IS NULL
             AND vigencia_inicio <= ?
             AND (vigencia_fim IS NULL OR vigencia_fim > ?)
           ORDER BY vigencia_inicio DESC""",
        (politica, mes_inicio, mes_inicio),
    ).fetchall()
    result: dict[str, str] = {}
    for r in rows:
        result.setdefault(r["chave"], r["valor"])
    return result


def _tab_parametros(con):
    from datetime import datetime, date

    st.subheader("Parâmetros de política")
    st.caption(
        "Cada alteração cria uma nova vigência — os meses já publicados continuam "
        "usando os parâmetros da época (RN-20/21)."
    )

    hoje = date.today().strftime("%Y-%m-%d")

    for politica, meta in _POLITICAS_CAMPOS.items():
        with st.expander(f"**{meta['label']}** — {politica}", expanded=False):
            # Valores vigentes hoje
            atual = _params_vigentes(con, politica, hoje)

            st.markdown("**Valores vigentes hoje:**")
            cols = st.columns(len(meta["campos"]))
            for i, (chave, label) in enumerate(meta["campos"]):
                cols[i].metric(label, atual.get(chave, "—"))

            st.markdown("---")
            st.markdown("**Nova vigência:**")

            with st.form(key=f"form_{politica}"):
                vig_inicio = st.date_input(
                    "Vigência a partir de",
                    value=date.today(),
                    key=f"vig_{politica}",
                )
                alterado_por = st.text_input("Alterado por", value="Arthur", key=f"autor_{politica}")

                novos: dict[str, str] = {}
                col_forms = st.columns(min(3, len(meta["campos"])))
                for i, (chave, label) in enumerate(meta["campos"]):
                    val_atual = atual.get(chave, "0")
                    novos[chave] = col_forms[i % 3].text_input(
                        label, value=val_atual, key=f"{politica}_{chave}"
                    )

                salvar = st.form_submit_button("💾 Salvar nova vigência")

            if salvar:
                vig_str = vig_inicio.strftime("%Y-%m-%d")
                agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                # Fecha vigência anterior (apenas parâmetros gerais, não por profissional)
                con.execute(
                    """UPDATE parametros SET vigencia_fim=?
                       WHERE politica=? AND vigencia_fim IS NULL AND profissional IS NULL""",
                    (vig_str, politica),
                )
                # Insere novos valores
                for chave, valor in novos.items():
                    con.execute(
                        """INSERT INTO parametros
                           (politica, chave, valor, vigencia_inicio, vigencia_fim, alterado_por, alterado_em)
                           VALUES (?,?,?,?,NULL,?,?)""",
                        (politica, chave, valor, vig_str, alterado_por, agora),
                    )
                con.commit()
                st.success(f"Nova vigência salva a partir de {vig_str}.")
                st.rerun()

            # Histórico de vigências
            hist = con.execute(
                """SELECT vigencia_inicio, vigencia_fim, chave, valor, alterado_por, alterado_em
                   FROM parametros WHERE politica=? AND profissional IS NULL
                   ORDER BY vigencia_inicio DESC, chave""",
                (politica,),
            ).fetchall()
            if hist:
                with st.expander("Histórico de vigências"):
                    df_h = pd.DataFrame([dict(r) for r in hist])
                    df_h["vigencia_fim"] = df_h["vigencia_fim"].fillna("aberto")
                    st.dataframe(df_h, width="stretch", hide_index=True)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if db.dialect() == "sqlite" and not os.path.exists(
        os.path.join(os.path.dirname(__file__), "..", "db", "gansos.db")
    ):
        st.error("Banco não encontrado. Rode: `python init_db.py` e depois importe os arquivos.")
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
