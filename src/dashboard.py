"""
src/dashboard.py — Dashboard Gansos Hub.
Uso: streamlit run src/dashboard.py
"""
import os

import altair as alt
import pandas as pd
import streamlit as st

import src.db as db

st.set_page_config(
    page_title="Gansos Hub",
    layout="wide",
)


# ---------------------------------------------------------------------------
# Utilitários
# ---------------------------------------------------------------------------

_MESES_PT = {
    "01": "Janeiro", "02": "Fevereiro", "03": "Março", "04": "Abril",
    "05": "Maio", "06": "Junho", "07": "Julho", "08": "Agosto",
    "09": "Setembro", "10": "Outubro", "11": "Novembro", "12": "Dezembro",
}

_MESES_CURTO_PT = {
    "01": "jan", "02": "fev", "03": "mar", "04": "abr",
    "05": "mai", "06": "jun", "07": "jul", "08": "ago",
    "09": "set", "10": "out", "11": "nov", "12": "dez",
}


def _fmt_mes(mes: str) -> str:
    if not mes or len(mes) < 7 or "-" not in mes:
        return str(mes)
    ano, m = mes[:4], mes[5:7]
    nome = _MESES_PT.get(m)
    return f"{nome} {ano}" if nome else mes


def _fmt_mes_curto(mes: str) -> str:
    if not mes or len(mes) < 7 or "-" not in mes:
        return str(mes)
    ano, m = mes[2:4], mes[5:7]
    nome = _MESES_CURTO_PT.get(m)
    return f"{nome}/{ano}" if nome else mes


@st.cache_resource
def _conectar():
    return db.conectar()


def _con():
    return _conectar()


@st.cache_data(ttl=600)
def _meses_disponiveis() -> list[str]:
    with db.conectar() as con:
        rows = con.execute(
            f"SELECT DISTINCT {db.mes_expr('data_hora')} as mes FROM vendas ORDER BY mes DESC"
        ).fetchall()
        return [r[0] for r in rows]


def _fmt_brl(v: float | None) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "—"
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _fmt_brl_md(v: float | None) -> str:
    """Versão para textos Markdown/caption do Streamlit (escapa $ para não abrir KaTeX)."""
    return _fmt_brl(v).replace("$", "\\$")


def _nivel_badge(nivel: str | None) -> str:
    if nivel is None or (isinstance(nivel, float) and pd.isna(nivel)):
        return "Sem classificação"
    s = str(nivel).strip()
    if not s or s.lower() in ("none", "nan"):
        return "Sem classificação"
    return s


# ---------------------------------------------------------------------------
# Aba 1 — Vendas (com cache de dados)
# ---------------------------------------------------------------------------

@st.cache_data(ttl=600)
def _get_vendas_mes_data(mes: str):
    with db.conectar() as con:
        rows = con.execute(
            f"""SELECT tipo,
                      ROUND(SUM(valor), 2) as total,
                      COUNT(*) as qtd
               FROM vendas
               WHERE {db.mes_expr('data_hora')} = ?
               GROUP BY tipo""",
            (mes,),
        ).fetchall()
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
    return [dict(r) for r in rows], [dict(r) for r in prof_rows]


@st.cache_data(ttl=1800)
def _get_receita_hist():
    with db.conectar() as con:
        hist = con.execute(
            f"""SELECT {db.mes_expr('data_hora')} as mes,
                      tipo,
                      ROUND(SUM(valor), 2) as total
               FROM vendas
               GROUP BY mes, tipo
               ORDER BY mes""",
        ).fetchall()
    return [dict(r) for r in hist]


def _tab_vendas(con, mes: str):
    st.subheader(f"Receita — {_fmt_mes(mes)}")

    rows, prof_rows = _get_vendas_mes_data(mes)

    total_mes = sum(r["total"] for r in rows)
    c1, c2, c3 = st.columns(3)
    for r in rows:
        col = c1 if r["tipo"] == "Serviço" else c2
        col.metric(r["tipo"], _fmt_brl(r["total"]), f"{r['qtd']} lançamentos")
    c3.metric("Total geral", _fmt_brl(total_mes))

    st.divider()

    # Comparativo mensal
    st.markdown("#### Receita mensal — todos os meses")
    hist = _get_receita_hist()
    df_hist = pd.DataFrame(hist)
    if not df_hist.empty:
        df_hist["mes_curto"] = df_hist["mes"].map(_fmt_mes_curto)
        df_hist["mes_nome"] = df_hist["mes"].map(_fmt_mes)
        df_hist["total_fmt"] = df_hist["total"].map(_fmt_brl)
        df_hist["ordem"] = df_hist["tipo"].map(lambda t: 1 if t == "Produto" else 2)
        chart_hist = (
            alt.Chart(df_hist)
            .mark_bar()
            .encode(
                x=alt.X(
                    "mes_curto:N",
                    title=None,
                    sort=alt.EncodingSortField(field="mes", order="ascending"),
                    axis=alt.Axis(labelAngle=0),
                ),
                y=alt.Y("total:Q", title=None, axis=alt.Axis(format="~s")),
                color=alt.Color(
                    "tipo:N",
                    title=None,
                    scale=alt.Scale(
                        domain=["Produto", "Serviço"],
                        range=["#27272A", "#D4D4D8"],
                    ),
                    legend=alt.Legend(orient="top"),
                ),
                order=alt.Order("ordem:Q", sort="ascending"),
                tooltip=[
                    alt.Tooltip("mes_nome:N", title="Mês"),
                    alt.Tooltip("tipo:N", title="Tipo"),
                    alt.Tooltip("total_fmt:N", title="Valor"),
                ],
            )
            .properties(height=300)
        )
        st.altair_chart(chart_hist, use_container_width=True)

    st.divider()

    # Receita por profissional no mês (pivotada: Profissional | Serviço | Produtos | Total)
    st.markdown("#### Receita por profissional no mês")
    if prof_rows:
        df_prof = pd.DataFrame(prof_rows)
        df_piv = df_prof.pivot_table(
            index="profissional",
            columns="tipo",
            values="total",
            aggfunc="sum",
            fill_value=0.0,
        ).reset_index()
        if "Serviço" not in df_piv.columns:
            df_piv["Serviço"] = 0.0
        if "Produto" not in df_piv.columns:
            df_piv["Produto"] = 0.0
        df_piv["Total"] = df_piv["Serviço"] + df_piv["Produto"]
        df_piv = df_piv.sort_values("Total", ascending=False)
        df_exib = pd.DataFrame({
            "Profissional": df_piv["profissional"],
            "Serviço": df_piv["Serviço"].astype(float),
            "Produtos": df_piv["Produto"].astype(float),
            "Total": df_piv["Total"].astype(float),
        })
        st.dataframe(
            df_exib,
            width="stretch",
            hide_index=True,
            column_config={
                "Serviço": st.column_config.NumberColumn("Serviço", format="R$ %.2f"),
                "Produtos": st.column_config.NumberColumn("Produtos", format="R$ %.2f"),
                "Total": st.column_config.NumberColumn("Total", format="R$ %.2f"),
            },
        )


# ---------------------------------------------------------------------------
# Helpers de publicação e aviso parcial
# ---------------------------------------------------------------------------

def _aviso_mes_parcial(con, mes: str, setor: dict):
    """Se o último dia com venda não é o último do mês, mostra o ritmo necessário."""
    import calendar
    from datetime import date

    ultimo, dias = con.execute(
        f"""SELECT MAX({db.date_expr('data_hora')}), COUNT(DISTINCT {db.date_expr('data_hora')})
           FROM vendas WHERE {db.mes_expr('data_hora')} = ?""",
        (mes,),
    ).fetchone()
    if not ultimo:
        return
    ano, m = int(mes[:4]), int(mes[5:7])
    fim_mes = calendar.monthrange(ano, m)[1]
    if int(str(ultimo)[8:10]) >= fim_mes - 1:
        return
    restantes = sum(
        1 for d in range(int(str(ultimo)[8:10]) + 1, fim_mes + 1)
        if date(ano, m, d).weekday() != 6
    )
    ritmo = setor["faturamento"] / dias if dias else 0
    msg = (
        f"Mês em andamento: dados até {str(ultimo)[8:10]}/{mes[5:7]} ({dias} dias com movimento, "
        f"ritmo médio {_fmt_brl(ritmo)}/dia). O nível do setor só vale no fechamento do mês."
    )
    if restantes:
        faltam = {n: max(setor["metas"][n] - setor["faturamento"], 0) / restantes for n in ("Bronze", "Prata", "Ouro")}
        msg += (
            f" Restam {restantes} dias (seg–sáb): para Bronze, {_fmt_brl(faltam['Bronze'])}/dia · "
            f"Prata, {_fmt_brl(faltam['Prata'])}/dia · Ouro, {_fmt_brl(faltam['Ouro'])}/dia."
        )
    st.info(msg.replace("$", "\\$"))


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
    st.cache_data.clear()


def _bloco_apuracao(con, mes: str, politica: str, label: str, linhas: list[dict],
                    col_extra: list[str], rename: dict, pode_publicar: bool = True) -> float:
    """Renderiza bloco de apuração com botão publicar / badge publicado."""
    pub = _apuracao_publicada(con, mes, politica)

    if pub:
        st.success(f"Publicada em {pub['publicada_em']} — exibindo snapshot imutável.")
        linhas_exib = pub["payload"]
    else:
        linhas_exib = linhas

    df = pd.DataFrame(linhas_exib)
    if df.empty:
        st.info(f"Nenhum(a) {label.lower()} com movimento neste mês.")
        return 0.0

    if "nivel" in df.columns:
        df["nivel"] = df["nivel"].apply(_nivel_badge)
    if "elegivel" in df.columns:
        if "elegivel" in col_extra:
            df["elegivel"] = df["elegivel"].map(
                lambda v: "Sim" if v is True or str(v).lower() == "true" else "Não"
            )
        else:
            df = df[df["elegivel"].astype(str).isin(["True", "true", True])]

    cols_show = [c for c in col_extra if c in df.columns]
    col_cfg = {}
    for col in ["faturamento", "gratificacao", "receita", "ticket_medio"]:
        if col in cols_show:
            df[col] = pd.to_numeric(df[col], errors="coerce")
            col_label = rename.get(col, col)
            col_cfg[col_label] = st.column_config.NumberColumn(col_label, format="R$ %.2f")

    st.dataframe(
        df[cols_show].rename(columns=rename),
        width="stretch",
        hide_index=True,
        column_config=col_cfg,
    )

    grat = sum(r.get("gratificacao", 0) for r in linhas_exib)
    st.caption(f"Subtotal {label.lower()}: {_fmt_brl_md(grat)}")

    if not pub and pode_publicar:
        if st.button(f"Publicar apuração — {label} {_fmt_mes(mes)}", key=f"pub_{politica}_{mes}"):
            _publicar(con, mes, politica, linhas)
            st.success("Apuração publicada! Recarregue para ver o badge.")
            st.rerun()

    return grat


# ---------------------------------------------------------------------------
# Aba 3 — Apuração (com Cache de Dados e Resumo Consolidado de Pagamentos)
# ---------------------------------------------------------------------------

@st.cache_data(ttl=600)
def _dados_apuracao_cached(mes: str):
    from src.apuracao_barbeiros import apurar_barbeiros, resumo_setor, _stats_mes
    from src.apuracao_faturamento import apurar_faturamento, apurar_recepcao_caixa, _get_params_fat

    with db.conectar() as con:
        try:
            barb = apurar_barbeiros(mes, con)
            setor = resumo_setor(mes, con)
        except ValueError:
            stats = _stats_mes(mes, con)
            barb = [
                {
                    "nome": nome,
                    "atendimentos": atend,
                    "receita": round(receita, 2),
                    "ticket_medio": round(receita / atend, 2) if atend else 0.0,
                    "nivel": None,
                    "gratificacao": 0.0,
                    "modelo": "sem_politica",
                }
                for nome, (atend, receita) in stats.items()
            ]
            setor = None

        manic = apurar_faturamento(mes, "manicures", con)
        for r in manic:
            p = _get_params_fat("manicures", mes, con, profissional=r["nome"])
            if p and "bronze_meta" in p:
                r["metas"] = f"B: {_fmt_brl(float(p['bronze_meta']))} | P: {_fmt_brl(float(p['prata_meta']))} | O: {_fmt_brl(float(p['ouro_meta']))}"
            else:
                r["metas"] = "—"

        assist = apurar_faturamento(mes, "assistentes", con)
        for r in assist:
            p = _get_params_fat("assistentes", mes, con, profissional=r["nome"])
            if p and "bronze_meta" in p:
                r["metas"] = f"B: {_fmt_brl(float(p['bronze_meta']))} | P: {_fmt_brl(float(p['prata_meta']))} | O: {_fmt_brl(float(p['ouro_meta']))}"
                if "diamante_meta" in p:
                    r["metas"] += f" | D: {_fmt_brl(float(p['diamante_meta']))}"
            else:
                r["metas"] = "—"

        recep = apurar_recepcao_caixa(mes, con)
        p_recep = _get_params_fat("recepcao_caixa", mes, con)
        metas_recep_str = (
            f"B: {_fmt_brl(float(p_recep['bronze_meta']))} | P: {_fmt_brl(float(p_recep['prata_meta']))} | O: {_fmt_brl(float(p_recep['ouro_meta']))}"
            if p_recep and "bronze_meta" in p_recep else ""
        )
        for r in recep:
            r["metas"] = metas_recep_str

    for r in barb:
        if r.get("modelo") == "setor_tm":
            if r.get("piso_bronze") is not None:
                r["metas"] = f"B: {_fmt_brl(r['piso_bronze'])} | P: {_fmt_brl(r['piso_prata'])} | O: {_fmt_brl(r['piso_ouro'])}"
            elif r.get("tm_base") is not None:
                r["metas"] = f"Base: {_fmt_brl(r['tm_base'])}"
            else:
                r["metas"] = "—"

    return barb, setor, manic, assist, recep, metas_recep_str


def _tab_apuracao(con, mes: str):
    st.subheader(f"Apuração do mês — {_fmt_mes(mes)}")

    barb, setor, manic, assist, recep, metas_recep_str = _dados_apuracao_cached(mes)

    total_grat = (
        sum(r.get("gratificacao", 0) for r in barb) +
        sum(r.get("gratificacao", 0) for r in manic) +
        sum(r.get("gratificacao", 0) for r in assist) +
        sum(r.get("gratificacao", 0) for r in recep)
    )

    # 1. Resumo Executivo Consolidado de Pagamentos
    st.markdown("### Resumo Consolidado de Pagamentos")
    st.caption("Quadro geral trazendo quem vai receber e quanto vai receber com base nas metas atingidas:")

    premiados = []
    for r in barb:
        if r.get("gratificacao", 0) > 0:
            if r.get("modelo") == "setor_tm":
                criterio_barb = f"TM {_fmt_brl(r.get('ticket_medio'))} (Base {_fmt_brl(r.get('tm_base'))})"
            else:
                criterio_barb = f"TM {_fmt_brl(r.get('ticket_medio'))} ({r.get('atendimentos', 0)} atend.)"
            premiados.append({
                "Colaborador": r["nome"],
                "Setor": "Barbeiro",
                "Meta / Nível": _nivel_badge(r.get("nivel")),
                "Critério / Desempenho": criterio_barb,
                "Valor a Receber": float(r.get("gratificacao", 0)),
            })
    for r in manic:
        if r.get("gratificacao", 0) > 0:
            premiados.append({
                "Colaborador": r["nome"],
                "Setor": "Manicure",
                "Meta / Nível": _nivel_badge(r.get("nivel")),
                "Critério / Desempenho": f"Faturamento de {_fmt_brl(r.get('faturamento'))}",
                "Valor a Receber": float(r.get("gratificacao", 0)),
            })
    for r in assist:
        if r.get("gratificacao", 0) > 0:
            premiados.append({
                "Colaborador": r["nome"],
                "Setor": "Assistente",
                "Meta / Nível": _nivel_badge(r.get("nivel")),
                "Critério / Desempenho": f"Faturamento de {_fmt_brl(r.get('faturamento'))}",
                "Valor a Receber": float(r.get("gratificacao", 0)),
            })
    for r in recep:
        if r.get("gratificacao", 0) > 0:
            premiados.append({
                "Colaborador": r["nome"],
                "Setor": "Recepção / Caixa",
                "Meta / Nível": _nivel_badge(r.get("nivel")),
                "Critério / Desempenho": f"Venda individual {_fmt_brl(r.get('faturamento'))}",
                "Valor a Receber": float(r.get("gratificacao", 0)),
            })

    if premiados:
        df_prem = pd.DataFrame(premiados)
        st.dataframe(
            df_prem,
            width="stretch",
            hide_index=True,
            column_config={
                "Valor a Receber": st.column_config.NumberColumn("Valor a Receber", format="R$ %.2f"),
            },
        )
        st.success(f"**Total Geral de Gratificações a Pagar:** {_fmt_brl_md(total_grat)} ({len(premiados)} colaboradores premiados)")
    else:
        st.info(f"Nenhum colaborador com gratificação consolidada até o momento para {_fmt_mes(mes)}.")

    st.divider()

    # 2. Detalhamento por Setor
    st.markdown("#### Barbeiros")
    modelo_barb = barb[0].get("modelo") if barb else ("setor_tm" if setor else None)
    if modelo_barb == "setor_tm":
        if setor:
            if setor["metas"]:
                _aviso_mes_parcial(con, mes, setor)
            c1, c2, c3 = st.columns(3)
            delta_str = (
                f"{setor['variacao_pct']:+.1f}% vs base {_fmt_brl(setor['base'])}"
                if setor["variacao_pct"] is not None and setor["base"] is not None
                else None
            )
            c1.metric("Faturamento do setor", _fmt_brl(setor["faturamento"]), delta_str)
            c2.metric("Nível do setor (Gate)", _nivel_badge(setor["nivel"]))
            if setor["metas"]:
                prox = next((n for n in ("Bronze", "Prata", "Ouro") if setor["faturamento"] < setor["metas"][n]), None)
                if prox:
                    c3.metric(f"Falta para {prox}", _fmt_brl(setor["metas"][prox] - setor["faturamento"]))
                else:
                    c3.metric("Meta Ouro", "Atingida")
                m = {n: _fmt_brl(setor["metas"][n]).replace("$", "\\$") for n in ("Bronze", "Prata", "Ouro")}
                st.info(
                    f"**Metas Coletivas do Setor (Gate):** Bronze ≥ **{m['Bronze']}** · Prata ≥ **{m['Prata']}** · Ouro ≥ **{m['Ouro']}**\n\n"
                    f"*(Base: {_fmt_brl(setor['base']).replace('$', chr(92) + '$')} — média dos 3 meses anteriores. Nível efetivo = menor entre setor e TM individual)*"
                )

        _bloco_apuracao(
            con, mes, "barbeiros", "Barbeiros", barb,
            col_extra=["nome", "atendimentos", "ticket_medio", "receita", "metas", "nivel", "gratificacao"],
            rename={"nome": "Barbeiro", "atendimentos": "Atend.", "ticket_medio": "TM",
                    "receita": "Faturamento", "metas": "Metas TM (B/P/O)",
                    "nivel": "Nível", "gratificacao": "Gratificação"},
        )
    elif modelo_barb == "legado":
        fat_geral = sum(r.get("receita", 0) for r in barb)
        st.metric("Faturamento geral dos barbeiros", _fmt_brl(fat_geral))
        st.info(
            "**Critério (Modelo Legado v1):** Ticket Médio vs. metas absolutas — "
            "Bronze ≥ **R\\$ 120,00** · Prata ≥ **R\\$ 135,00** · Ouro ≥ **R\\$ 150,00** "
            "(elegibilidade: ≥ 50 atendimentos)."
        )
        _bloco_apuracao(
            con, mes, "barbeiros", "Barbeiros", barb,
            col_extra=["nome", "atendimentos", "ticket_medio", "receita", "elegivel", "nivel", "gratificacao"],
            rename={"nome": "Barbeiro", "atendimentos": "Atend.", "ticket_medio": "TM",
                    "receita": "Faturamento", "elegivel": "Elegível",
                    "nivel": "Nível", "gratificacao": "Gratificação"},
        )
    elif modelo_barb == "sem_politica":
        fat_geral = sum(r.get("receita", 0) for r in barb)
        st.metric("Faturamento geral dos barbeiros", _fmt_brl(fat_geral))
        st.caption(f"Sem política de gratificação vigente para {_fmt_mes(mes)} — exibindo apenas a base de serviços.")
        _bloco_apuracao(
            con, mes, "barbeiros", "Barbeiros", barb,
            col_extra=["nome", "atendimentos", "ticket_medio", "receita", "nivel", "gratificacao"],
            rename={"nome": "Barbeiro", "atendimentos": "Atend.", "ticket_medio": "TM",
                    "receita": "Faturamento", "nivel": "Nível", "gratificacao": "Gratificação"},
            pode_publicar=False,
        )
    else:
        st.info(f"Sem movimento de barbeiros em {_fmt_mes(mes)}.")

    st.markdown("#### Manicures")
    _bloco_apuracao(
        con, mes, "manicures", "Manicures", manic,
        col_extra=["nome", "faturamento", "metas", "nivel", "gratificacao"],
        rename={"nome": "Manicure", "faturamento": "Faturamento", "metas": "Metas (B/P/O)",
                "nivel": "Nível", "gratificacao": "Gratificação"},
    )

    st.markdown("#### Assistentes")
    _bloco_apuracao(
        con, mes, "assistentes", "Assistentes", assist,
        col_extra=["nome", "faturamento", "metas", "nivel", "gratificacao"],
        rename={"nome": "Assistente", "faturamento": "Faturamento", "metas": "Metas (B/P/O)",
                "nivel": "Nível", "gratificacao": "Gratificação"},
    )

    st.markdown("#### Recepção / Caixa")
    total_setor_recep = recep[0]["total_setor"] if recep else 0.0
    metas_recep_md = metas_recep_str.replace("$", "\\$")
    st.caption(f"Meta coletiva de produtos — total do setor: {_fmt_brl_md(total_setor_recep)} ({metas_recep_md})")
    _bloco_apuracao(
        con, mes, "recepcao_caixa", "Recepção/Caixa", recep,
        col_extra=["nome", "faturamento", "metas", "nivel", "gratificacao"],
        rename={"nome": "Profissional", "faturamento": "Venda Individual", "metas": "Metas Coletivas",
                "nivel": "Nível", "gratificacao": "Gratificação"},
    )


# ---------------------------------------------------------------------------
# Aba 4 — Parâmetros (edição com vigência — RN-20)
# ---------------------------------------------------------------------------

_POLITICAS_CAMPOS = {
    "gratificacao_barbeiros": {
        "label": "Barbeiros",
        "campos": [
            ("modelo",                "Modelo (setor_tm)"),
            ("setor_base_meses",      "Setor — meses da base"),
            ("setor_bronze_pct",      "Setor Bronze — crescimento (0.07 = 7%)"),
            ("setor_prata_pct",       "Setor Prata — crescimento"),
            ("setor_ouro_pct",        "Setor Ouro — crescimento"),
            ("tm_baseline_meses",     "TM — meses do baseline"),
            ("tm_baseline_min_meses", "TM — mínimo de meses de histórico"),
            ("tm_bronze_pct",         "TM Bronze — acima do baseline"),
            ("tm_prata_pct",          "TM Prata — acima do baseline"),
            ("tm_ouro_pct",           "TM Ouro — acima do baseline"),
            ("bronze_premio",         "Bronze — Prêmio (R$)"),
            ("prata_premio",          "Prata — Prêmio (R$)"),
            ("ouro_premio",           "Ouro — Prêmio (R$)"),
            ("minimo_atendimentos",   "Mínimo de atendimentos (0 = sem piso)"),
            ("pdi_atend_pct",         "PDI atendimentos — acima do baseline"),
            ("excluidos",             "Excluídos do setor (nomes separados por |)"),
            ("baseline_como",         "Baseline emprestado (A>B|C>D)"),
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
            ("diamante_meta", "Diamante — Meta fat. (R$)"),
            ("diamante_premio", "Diamante — Prêmio (R$)"),
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
            campos = meta["campos"]
            for ini in range(0, len(campos), 6):
                grupo = campos[ini:ini + 6]
                for col, (chave, label) in zip(st.columns(len(grupo)), grupo):
                    col.metric(label, atual.get(chave, "—"))

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

                salvar = st.form_submit_button("Salvar nova vigência")

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

    st.divider()
    st.markdown("### Parâmetros Individuais por Profissional")
    st.caption("Metas e baselines atribuídos a profissionais específicos (ex: Manicures, Pedro Ian).")
    indiv_rows = con.execute(
        """SELECT profissional, politica, chave, valor, vigencia_inicio, vigencia_fim, alterado_por
           FROM parametros WHERE profissional IS NOT NULL
           ORDER BY profissional, chave"""
    ).fetchall()
    if indiv_rows:
        df_indiv = pd.DataFrame([dict(r) for r in indiv_rows])
        df_indiv["vigencia_fim"] = df_indiv["vigencia_fim"].fillna("vigente")
        st.dataframe(
            df_indiv.rename(columns={
                "profissional": "Profissional",
                "politica": "Política",
                "chave": "Parâmetro",
                "valor": "Valor (R$)",
                "vigencia_inicio": "Início",
                "vigencia_fim": "Fim",
                "alterado_por": "Autor",
            }),
            width="stretch", hide_index=True
        )

    # Formulário para definir/alterar Base de TM de Barbeiro
    with st.expander("Definir Base de TM para Barbeiro (Provisória / Individual)", expanded=False):
        barbeiros_rows = con.execute(
            "SELECT nome_sistema FROM profissionais WHERE funcao='barbeiro' AND ativo=1 ORDER BY nome_sistema"
        ).fetchall()
        nomes_barb = [r["nome_sistema"] for r in barbeiros_rows]

        with st.form("form_base_barbeiro"):
            barb_sel = st.selectbox("Barbeiro", nomes_barb)
            base_val = st.number_input("Valor da Base de TM (R$)", min_value=50.0, max_value=500.0, value=122.93, step=1.0)
            vig_barb = st.date_input("Vigência a partir de", value=date.today(), key="vig_barb")
            autor_barb = st.text_input("Alterado por", value="Arthur", key="autor_barb")
            salvar_barb = st.form_submit_button("Salvar Base Individual")

        if salvar_barb:
            vig_b_str = vig_barb.strftime("%Y-%m-%d")
            agora_b = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            con.execute(
                """UPDATE parametros SET vigencia_fim=?
                   WHERE politica='gratificacao_barbeiros' AND chave='tm_base_fixa'
                     AND profissional=? AND vigencia_fim IS NULL""",
                (vig_b_str, barb_sel),
            )
            con.execute(
                """INSERT INTO parametros
                   (politica, chave, valor, vigencia_inicio, vigencia_fim, alterado_por, alterado_em, profissional)
                   VALUES ('gratificacao_barbeiros', 'tm_base_fixa', ?, ?, NULL, ?, ?, ?)""",
                (f"{base_val:.2f}", vig_b_str, autor_barb, agora_b, barb_sel),
            )
            con.commit()
            st.success(f"Base de TM de {_fmt_brl(base_val)} salva para {barb_sel} a partir de {vig_b_str}!")
            st.rerun()


# ---------------------------------------------------------------------------
# Aba 2 — Análise Individual (com Cache e Renderização Leve)
# ---------------------------------------------------------------------------

@st.cache_data(ttl=600)
def _dados_analise_individual_cached(mes: str, setor_sel: str):
    from collections import defaultdict

    params_prof = [mes]
    if setor_sel != "Todos":
        setor_filter = "AND p.funcao = ?"
        params_prof.append(setor_sel)
    else:
        setor_filter = "AND p.funcao IN ('barbeiro', 'manicure', 'assistente')"

    with db.conectar() as con:
        query_setor_media = f"""
            SELECT sum(v.valor) as receita_total,
                   COUNT(DISTINCT {db.date_expr('v.data_hora')} || '|' || v.cliente) as atendimentos_total
            FROM vendas v
            JOIN profissionais p ON p.id = v.profissional_id
            WHERE v.tipo = 'Serviço' AND {db.mes_expr('v.data_hora')} = ?
              AND v.cliente IS NOT NULL AND v.cliente != ''
            {setor_filter}
        """
        row_media = con.execute(query_setor_media, tuple(params_prof)).fetchone()
        tm_setor = (row_media["receita_total"] / row_media["atendimentos_total"]) if row_media and row_media["atendimentos_total"] else 0

        query_prof = f"""
            SELECT p.id, p.nome_sistema, p.funcao,
                   COUNT(DISTINCT {db.date_expr('v.data_hora')} || '|' || v.cliente) as atendimentos,
                   SUM(v.valor) as receita
            FROM vendas v
            JOIN profissionais p ON v.profissional_id = p.id
            WHERE p.ativo = 1 AND v.tipo = 'Serviço' AND {db.mes_expr('v.data_hora')} = ?
              AND v.cliente IS NOT NULL AND v.cliente != ''
            {setor_filter}
            GROUP BY p.id, p.nome_sistema, p.funcao
        """
        profs = [dict(r) for r in con.execute(query_prof, tuple(params_prof)).fetchall()]

        if not profs:
            return tm_setor, []

        query_itens = f"""
            SELECT p.id as prof_id, v.item, sum(v.valor) as receita_item, count(*) as qtd_item
            FROM vendas v
            JOIN profissionais p ON v.profissional_id = p.id
            WHERE p.ativo = 1 AND v.tipo = 'Serviço' AND {db.mes_expr('v.data_hora')} = ?
              AND v.cliente IS NOT NULL AND v.cliente != ''
            {setor_filter}
            GROUP BY p.id, v.item
        """
        itens_rows = con.execute(query_itens, tuple(params_prof)).fetchall()

    itens_por_prof = defaultdict(list)
    for r in itens_rows:
        itens_por_prof[r["prof_id"]].append(dict(r))

    resultados = []
    for p in profs:
        prof_id = p["id"]
        receita = p["receita"]
        atendimentos = p["atendimentos"]
        tm = receita / atendimentos if atendimentos else 0

        itens = itens_por_prof.get(prof_id, [])
        itens.sort(key=lambda x: x["receita_item"], reverse=True)

        resultados.append({
            "id": prof_id,
            "nome": p["nome_sistema"],
            "funcao": p["funcao"],
            "tm": tm,
            "receita": receita,
            "atendimentos": atendimentos,
            "itens": itens,
        })

    resultados.sort(key=lambda x: x["tm"], reverse=True)
    return tm_setor, resultados


def _tab_analise_individual(con, mes: str):
    st.subheader(f"Análise Individual — {_fmt_mes(mes)}")

    setores_opcoes = ["Todos", "barbeiro", "manicure", "assistente"]
    col_setor, _ = st.columns([1, 3])
    with col_setor:
        setor_sel = st.selectbox(
            "Filtrar por Setor",
            setores_opcoes,
            format_func=lambda x: "Todos os setores" if x == "Todos" else x.capitalize(),
        )

    tm_setor, resultados = _dados_analise_individual_cached(mes, setor_sel)

    if not resultados:
        st.info("Nenhum atendimento encontrado para os filtros selecionados neste mês.")
        return

    st.markdown(f"**Média do setor selecionado (Ticket Médio):** {_fmt_brl_md(tm_setor)}")

    for res in resultados:
        with st.container(border=True):
            st.markdown(f"#### {res['nome']} · {res['funcao'].capitalize()}")

            delta_tm = ((res["tm"] / tm_setor) - 1) * 100 if tm_setor else 0
            delta_color = "normal" if delta_tm >= 0 else "inverse"

            mc1, mc2, mc3 = st.columns(3)
            mc1.metric("Ticket Médio", _fmt_brl(res["tm"]), f"{delta_tm:+.1f}%", delta_color=delta_color)
            mc2.metric("Atendimentos", res["atendimentos"])
            mc3.metric("Receita", _fmt_brl(res["receita"]))

            if res["itens"]:
                top_itens = sorted(res["itens"], key=lambda x: x["receita_item"], reverse=True)[:3]
                top_str = " · ".join([f"{it['item']} ({_fmt_brl_md(it['receita_item'])})" for it in top_itens])
                st.caption(f"**Top serviços:** {top_str}")

                df_itens = pd.DataFrame(res["itens"]).nlargest(5, "receita_item")
                total_prof = res["receita"] or df_itens["receita_item"].sum()
                df_itens["item_label"] = [f"{i + 1}. {row['item']}" for i, row in enumerate(df_itens.to_dict("records"))]
                df_itens["receita_fmt"] = df_itens["receita_item"].map(_fmt_brl)
                df_itens["pct_fmt"] = (df_itens["receita_item"] / total_prof * 100).map(lambda p: f"{p:.1f}%")

                tons_cinza = ["#27272A", "#52525B", "#71717A", "#A1A1AA", "#D4D4D8"]
                chart = (
                    alt.Chart(df_itens)
                    .mark_bar(size=28)
                    .encode(
                        x=alt.X("receita_item:Q", stack="zero", title=None, axis=alt.Axis(format="~s")),
                        y=alt.Y("prof_id:N", title=None, axis=alt.Axis(labels=False, ticks=False, domain=False)),
                        color=alt.Color(
                            "item_label:N",
                            sort=alt.EncodingSortField(field="receita_item", op="max", order="descending"),
                            scale=alt.Scale(range=tons_cinza),
                            legend=alt.Legend(title=None, orient="bottom", columns=2, labelLimit=160),
                        ),
                        order=alt.Order("receita_item:Q", sort="descending"),
                        tooltip=[
                            alt.Tooltip("item:N", title="Serviço"),
                            alt.Tooltip("receita_fmt:N", title="Receita"),
                            alt.Tooltip("pct_fmt:N", title="% da receita"),
                        ],
                    )
                    .properties(height=140)
                )
                st.altair_chart(chart, use_container_width=True)
            else:
                st.caption("Sem serviços registrados no mês.")


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
    meses = _meses_disponiveis()

    if not meses:
        st.warning("Nenhum dado importado. Rode `python src/ingestao.py <arquivo.xlsx>`.")
        return

    st.title("Gansos Hub")

    col_mes, _ = st.columns([1, 3])
    with col_mes:
        mes_sel = st.selectbox("Mês", meses, index=0, format_func=_fmt_mes)

    t1, t2, t3, t4 = st.tabs(["Vendas", "Análise Individual", "Apuração", "Parâmetros"])

    with t1:
        _tab_vendas(con, mes_sel)
    with t2:
        _tab_analise_individual(con, mes_sel)
    with t3:
        _tab_apuracao(con, mes_sel)
    with t4:
        _tab_parametros(con)


if __name__ == "__main__":
    main()
