"""
Gera documento formatado da Apuração de Gratificações (HTML imprimível/copiável e apresentação executiva).
"""
import os
import sys
import src.db as db
import src.apuracao_barbeiros as ab
import src.apuracao_faturamento as af

def fmt_brl(val):
    if val is None:
        return "—"
    return f"R$ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def gerar_apuracao_doc(mes: str = "2026-10", out_html: str = "apuracao_outubro_2026.html"):
    con = db.conectar()
    
    setor_barb = ab.resumo_setor(mes, con)
    barbeiros = ab.apurar_barbeiros(mes, con)
    manicures = af.apurar_faturamento(mes, "manicures", con)
    assistentes = af.apurar_faturamento(mes, "assistentes", con)
    recepcao = af.apurar_recepcao_caixa(mes, con)
    p_recep = af._get_params_fat("recepcao_caixa", mes, con)

    total_grat = (
        sum(r.get("gratificacao", 0) for r in barbeiros) +
        sum(r.get("gratificacao", 0) for r in manicures) +
        sum(r.get("gratificacao", 0) for r in assistentes) +
        sum(r.get("gratificacao", 0) for r in recepcao)
    )

    premiados = []
    for r in barbeiros:
        if r.get("gratificacao", 0) > 0:
            premiados.append({
                "nome": r["nome"],
                "setor": "Barbeiro",
                "nivel": r.get("nivel"),
                "criterio": f"TM {fmt_brl(r.get('ticket_medio'))} (Base {fmt_brl(r.get('tm_base'))})",
                "gratificacao": r.get("gratificacao", 0),
            })
    for r in manicures:
        if r.get("gratificacao", 0) > 0:
            premiados.append({
                "nome": r["nome"],
                "setor": "Manicure",
                "nivel": r.get("nivel"),
                "criterio": f"Faturamento de {fmt_brl(r.get('faturamento'))}",
                "gratificacao": r.get("gratificacao", 0),
            })
    for r in assistentes:
        if r.get("gratificacao", 0) > 0:
            premiados.append({
                "nome": r["nome"],
                "setor": "Assistente",
                "nivel": r.get("nivel"),
                "criterio": f"Faturamento de {fmt_brl(r.get('faturamento'))}",
                "gratificacao": r.get("gratificacao", 0),
            })
    for r in recepcao:
        if r.get("gratificacao", 0) > 0:
            premiados.append({
                "nome": r["nome"],
                "setor": "Recepção / Caixa",
                "nivel": r.get("nivel"),
                "criterio": f"Venda individual {fmt_brl(r.get('faturamento'))} (Setor {fmt_brl(r.get('total_setor'))})",
                "gratificacao": r.get("gratificacao", 0),
            })

    linhas_prem_html = ""
    for p in premiados:
        badge_cls = "badge-nenhum"
        if p.get("nivel") == "Ouro": badge_cls = "badge-ouro"
        elif p.get("nivel") == "Prata": badge_cls = "badge-prata"
        elif p.get("nivel") == "Bronze": badge_cls = "badge-bronze"
        elif p.get("nivel") == "Diamante": badge_cls = "badge-ouro"

        linhas_prem_html += f"""
            <tr>
                <td class="nome-colaborador">{p['nome']}</td>
                <td>{p['setor']}</td>
                <td><span class="badge-nivel {badge_cls}">{p['nivel']}</span></td>
                <td>{p['criterio']}</td>
                <td style="text-align: right;"><strong>{fmt_brl(p['gratificacao'])}</strong></td>
            </tr>"""

    # HTML minimalista, executivo e moderno para tela e impressão A4 Paisagem
    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<title>Relatório de Apuração & Projeção Novembro — Gansos Barbearia</title>
<style>
    @page {{
        size: A4 landscape;
        margin: 12mm 15mm;
    }}
    * {{
        box-sizing: border-box;
    }}
    body {{
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
        color: #1a1a1a;
        background-color: #f4f5f7;
        line-height: 1.45;
        margin: 0;
        padding: 20px 0;
        -webkit-font-smoothing: antialiased;
    }}

    .pagina-setor {{
        background: #ffffff;
        max-width: 1080px;
        margin: 20px auto;
        padding: 30px 40px;
        border: 1px solid #e1e4e8;
        border-radius: 6px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        page-break-after: always;
        break-after: page;
    }}
    .pagina-setor:last-child {{
        page-break-after: avoid;
        break-after: avoid;
    }}

    @media print {{
        body {{
            background: #ffffff;
            color: #000000;
            padding: 0;
        }}
        .pagina-setor {{
            margin: 0;
            padding: 0;
            max-width: 100%;
            border: none;
            box-shadow: none;
            page-break-after: always;
            break-after: page;
        }}
        .pagina-setor:last-child {{
            page-break-after: avoid;
            break-after: avoid;
        }}
    }}

    .cabecalho {{
        display: flex;
        justify-content: space-between;
        align-items: baseline;
        border-bottom: 2px solid #111111;
        padding-bottom: 10px;
        margin-bottom: 18px;
    }}
    .cabecalho h1 {{
        margin: 0;
        font-size: 1.25em;
        font-weight: 700;
        letter-spacing: -0.3px;
        color: #111111;
        text-transform: uppercase;
    }}
    .cabecalho .mes {{
        font-size: 0.88em;
        color: #555555;
        font-weight: 600;
    }}

    .resumo-cards {{
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 12px;
        margin-bottom: 18px;
    }}
    .resumo-card {{
        background: #f8f9fa;
        border: 1px solid #e9ecef;
        border-radius: 4px;
        padding: 10px 14px;
    }}
    .resumo-card-label {{
        font-size: 0.7em;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        color: #666;
        margin-bottom: 3px;
        font-weight: 600;
    }}
    .resumo-card-val {{
        font-size: 1.15em;
        font-weight: 700;
        color: #111;
    }}
    .resumo-card-sub {{
        font-size: 0.72em;
        color: #28a745;
        font-weight: 600;
        margin-top: 2px;
    }}

    .titulo-secao {{
        font-size: 1.1em;
        font-weight: 700;
        color: #111111;
        margin: 0 0 12px 0;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }}
    .badge-total-setor {{
        font-size: 0.8em;
        background: #eef2f7;
        padding: 3px 9px;
        border-radius: 4px;
        font-weight: 600;
        color: #2b3a4a;
    }}

    /* Painel do Faturamento Coletivo (Gate) */
    .painel-gate {{
        border: 1px solid #dfe3e8;
        padding: 12px 16px;
        margin-bottom: 16px;
        background-color: #fafbfc;
        border-radius: 4px;
    }}
    .painel-gate-titulo {{
        font-size: 0.78em;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        font-weight: 700;
        color: #333333;
        margin-bottom: 8px;
    }}
    .gate-grid {{
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 12px;
        margin-bottom: 6px;
    }}
    .gate-item {{
        border-left: 3px solid #0066cc;
        padding-left: 10px;
    }}
    .gate-item.ouro {{
        border-left-color: #f1c40f;
    }}
    .gate-label {{
        font-size: 0.7em;
        color: #666666;
        text-transform: uppercase;
        margin-bottom: 2px;
        font-weight: 600;
    }}
    .gate-val {{
        font-size: 1em;
        font-weight: 700;
        color: #111111;
    }}
    .gate-obs {{
        font-size: 0.78em;
        color: #555555;
        margin-top: 4px;
        line-height: 1.4;
    }}

    table {{
        width: 100%;
        border-collapse: collapse;
        margin-top: 6px;
        margin-bottom: 16px;
    }}
    th {{
        text-align: left;
        font-size: 0.72em;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        font-weight: 700;
        color: #495057;
        background-color: #f8f9fa;
        border-top: 1px solid #dee2e6;
        border-bottom: 2px solid #212529;
        padding: 7px 9px;
    }}
    td {{
        padding: 7px 9px;
        font-size: 0.84em;
        border-bottom: 1px solid #e9ecef;
        color: #212529;
        vertical-align: middle;
    }}
    tr:last-child td {{
        border-bottom: 2px solid #dee2e6;
    }}
    tr:hover td {{
        background-color: #fdfdfd;
    }}
    .nome-colaborador {{
        font-weight: 600;
        color: #111111;
    }}

    .badge-nivel {{
        display: inline-block;
        padding: 2px 7px;
        border-radius: 4px;
        font-size: 0.8em;
        font-weight: 700;
        text-transform: uppercase;
    }}
    .badge-ouro {{ background: #fff3cd; color: #856404; border: 1px solid #ffeeba; }}
    .badge-prata {{ background: #e2e3e5; color: #383d41; border: 1px solid #d6d8db; }}
    .badge-bronze {{ background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }}
    .badge-nenhum {{ color: #888888; font-weight: normal; }}

    .faixa-meta {{
        display: inline-block;
        margin-right: 12px;
        white-space: nowrap;
        font-size: 0.88em;
    }}
    .faixa-nome {{
        font-size: 0.74em;
        font-weight: 700;
        color: #666666;
        text-transform: uppercase;
        margin-right: 3px;
    }}
    .faixa-val {{
        font-weight: 600;
        color: #222222;
    }}

    .proxima-meta {{
        font-size: 0.8em;
        color: #0056b3;
        font-weight: 500;
    }}
    .proxima-meta strong {{
        color: #d9534f;
    }}

    .tabela-premios {{
        font-size: 0.78em;
        color: #555555;
        padding-top: 6px;
        border-top: 1px solid #e9ecef;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }}
    .tabela-premios strong {{
        color: #222222;
    }}

    .box-info {{
        background: #e7f3fe;
        border-left: 4px solid #2196f3;
        padding: 9px 12px;
        margin-bottom: 14px;
        border-radius: 2px;
        font-size: 0.82em;
        color: #0c5460;
    }}
</style>
</head>
<body>

<!-- PÁGINA 1: RESUMO CONSOLIDADO DE PAGAMENTOS (QUEM RECEBE E QUANTO) -->
<div class="pagina-setor">
    <div class="cabecalho">
        <h1>Gansos Barbearia</h1>
        <div class="mes">Resumo Executivo de Pagamentos — {mes} (Fechamento Oficial)</div>
    </div>

    <div class="resumo-cards">
        <div class="resumo-card">
            <div class="resumo-card-label">Total Geral a Pagar</div>
            <div class="resumo-card-val" style="color: #28a745;">{fmt_brl(total_grat)}</div>
            <div class="resumo-card-sub">Folha de Gratificação</div>
        </div>
        <div class="resumo-card">
            <div class="resumo-card-label">Colaboradores Premiados</div>
            <div class="resumo-card-val">{len(premiados)} profissionais</div>
            <div class="resumo-card-sub">Metas Atingidas</div>
        </div>
        <div class="resumo-card">
            <div class="resumo-card-label">Gatilho do Setor (Gate)</div>
            <div class="resumo-card-val">Nível Ouro 🟡</div>
            <div class="resumo-card-sub">100% Liberado (+48,7%)</div>
        </div>
        <div class="resumo-card">
            <div class="resumo-card-label">Período Auditado</div>
            <div class="resumo-card-val">Mês Completo</div>
            <div class="resumo-card-sub">01/10 a 31/10/2026</div>
        </div>
    </div>

    <div class="titulo-secao">
        <span>Quadro Geral de Pagamento de Gratificações & Metas Atingidas</span>
        <span class="badge-total-setor">Folha Total: {fmt_brl(total_grat)}</span>
    </div>

    <div class="box-info">
        Demonstrativo consolidado de todos os profissionais que atingiram as metas oficiais estabelecidas para o mês de {mes}. O detalhamento específico de cada setor e as próximas metas de Novembro constam nas páginas seguintes.
    </div>

    <table>
        <thead>
            <tr>
                <th style="width: 28%;">Colaborador</th>
                <th style="width: 18%;">Setor / Função</th>
                <th style="width: 16%;">Meta Atingida</th>
                <th style="width: 24%;">Critério / Desempenho Real</th>
                <th style="width: 14%; text-align: right;">Gratificação</th>
            </tr>
        </thead>
        <tbody>
{linhas_prem_html}
            <tr style="background-color: #f8f9fa; font-weight: 700; border-top: 2px solid #212529;">
                <td colspan="4" style="text-align: right; padding: 10px 12px; font-size: 0.95em;">TOTAL GERAL DE GRATIFICAÇÕES A PAGAR:</td>
                <td style="text-align: right; padding: 10px 12px; font-size: 1.05em; color: #28a745;">{fmt_brl(total_grat)}</td>
            </tr>
        </tbody>
    </table>

    <div class="tabela-premios">
        <span><strong>Diretoria Gansos Barbearia:</strong> Relatório oficial consolidado para processamento de pagamentos.</span>
        <span>Gansos Hub — Sistema Integrado de Gestão</span>
    </div>
</div>

<!-- PÁGINA 2: BARBEIROS (OUTUBRO) -->
<div class="pagina-setor">
    <div class="cabecalho">
        <h1>Gansos Barbearia</h1>
        <div class="mes">Apuração & Comissões — {mes} (Mês Completo Fechado)</div>
    </div>

    <div class="resumo-cards">
        <div class="resumo-card">
            <div class="resumo-card-label">Total Gratificações</div>
            <div class="resumo-card-val">{fmt_brl(total_grat)}</div>
            <div class="resumo-card-sub">Barbearia Completa</div>
        </div>
        <div class="resumo-card">
            <div class="resumo-card-label">Fat. Serviços Setor</div>
            <div class="resumo-card-val">{fmt_brl(setor_barb['faturamento'] if setor_barb else 0)}</div>
            <div class="resumo-card-sub">+{setor_barb['variacao_pct'] if setor_barb else 0:.1f}% vs base</div>
        </div>
        <div class="resumo-card">
            <div class="resumo-card-label">Gatilho do Setor</div>
            <div class="resumo-card-val">Nível Ouro 🟡</div>
            <div class="resumo-card-sub">100% Liberado</div>
        </div>
        <div class="resumo-card">
            <div class="resumo-card-label">Atendimentos Barbeiros</div>
            <div class="resumo-card-val">{sum(r['atendimentos'] for r in barbeiros)}</div>
            <div class="resumo-card-sub">Clientes Únicos</div>
        </div>
    </div>

    <div class="titulo-secao">
        <span>1. Setor de Barbeiros — Apuração de Comissões & Metas (Outubro/2026)</span>
        <span class="badge-total-setor">Gratificação Setor: {fmt_brl(sum(r['gratificacao'] for r in barbeiros))}</span>
    </div>
"""

    if setor_barb:
        metas_s = setor_barb["metas"]
        html += f"""
    <div class="painel-gate">
        <div class="painel-gate-titulo">Gatilho Coletivo do Setor (Faturamento de Serviços da Barbearia)</div>
        <div class="gate-grid">
            <div class="gate-item">
                <div class="gate-label">Base Média (3M)</div>
                <div class="gate-val">{fmt_brl(setor_barb['base'])}</div>
            </div>
            <div class="gate-item">
                <div class="gate-label">Bronze</div>
                <div class="gate-val">{fmt_brl(metas_s['Bronze'])}</div>
            </div>
            <div class="gate-item">
                <div class="gate-label">Prata</div>
                <div class="gate-val">{fmt_brl(metas_s['Prata'])}</div>
            </div>
            <div class="gate-item ouro">
                <div class="gate-label">Ouro — Atingido!</div>
                <div class="gate-val">{fmt_brl(metas_s['Ouro'])}</div>
            </div>
        </div>
        <div class="gate-obs">
            Status: <strong>Gatilho OURO superado em +{setor_barb['variacao_pct']:.1f}%</strong> ({fmt_brl(setor_barb['faturamento'])} realizados). Todos os barbeiros estão liberados para receber a bonificação máxima de acordo com seu Ticket Médio individual.
        </div>
    </div>
"""

    html += """
    <table>
        <thead>
            <tr>
                <th style="width: 25%;">Barbeiro</th>
                <th style="width: 8%;">Atend.</th>
                <th style="width: 13%;">Receita</th>
                <th style="width: 10%;">TM Real</th>
                <th style="width: 10%;">Base TM</th>
                <th style="width: 10%;">Nível</th>
                <th style="width: 10%;">Gratificação</th>
                <th style="width: 14%;">Próxima Meta</th>
            </tr>
        </thead>
        <tbody>
"""
    for r in barbeiros:
        badge_cls = "badge-nenhum"
        if r.get("nivel") == "Ouro": badge_cls = "badge-ouro"
        elif r.get("nivel") == "Prata": badge_cls = "badge-prata"
        elif r.get("nivel") == "Bronze": badge_cls = "badge-bronze"
        
        nivel_label = r.get("nivel") or "—"
        tm_real = fmt_brl(r.get("ticket_medio"))
        base_tm = fmt_brl(r.get("tm_base"))
        rec = fmt_brl(r.get("receita"))
        grat = fmt_brl(r.get("gratificacao"))

        prox_str = "—"
        tm_val = r.get("ticket_medio") or 0.0
        pb = r.get("piso_bronze") or 0.0
        pp = r.get("piso_prata") or 0.0
        po = r.get("piso_ouro") or 0.0

        if r.get("nivel") == "Ouro":
            prox_str = "<span style='color:#28a745; font-weight:600;'>★ Teto Atingido</span>"
        elif r.get("nivel") == "Prata":
            dif = po - tm_val
            prox_str = f"<span class='proxima-meta'>Ouro: falta <strong>{fmt_brl(dif)}</strong> no TM</span>"
        elif r.get("nivel") == "Bronze":
            dif = pp - tm_val
            prox_str = f"<span class='proxima-meta'>Prata: falta <strong>{fmt_brl(dif)}</strong> no TM</span>"
        else:
            dif = pb - tm_val
            prox_str = f"<span class='proxima-meta'>Bronze: falta <strong>{fmt_brl(dif)}</strong> no TM</span>"

        html += f"""
            <tr>
                <td class="nome-colaborador">{r['nome']}</td>
                <td>{r['atendimentos']}</td>
                <td>{rec}</td>
                <td><strong>{tm_real}</strong></td>
                <td>{base_tm}</td>
                <td><span class="badge-nivel {badge_cls}">{nivel_label}</span></td>
                <td><strong>{grat}</strong></td>
                <td>{prox_str}</td>
            </tr>
"""
    html += """
        </tbody>
    </table>

    <div class="tabela-premios">
        <span><strong>Valores de Bonificação Individual:</strong> Bronze: R$ 150,00 &nbsp;|&nbsp; Prata: R$ 300,00 &nbsp;|&nbsp; Ouro: R$ 500,00</span>
        <span>Apuração oficial de gratificação por Ticket Médio.</span>
    </div>
</div>

<!-- PÁGINA 2: MANICURES (OUTUBRO) -->
<div class="pagina-setor">
    <div class="cabecalho">
        <h1>Gansos Barbearia</h1>
        <div class="mes">Apuração & Comissões — {mes} (Mês Completo Fechado)</div>
    </div>

    <div class="titulo-secao">
        <span>2. Setor de Manicures — Apuração de Comissões & Metas (Outubro/2026)</span>
        <span class="badge-total-setor">Gratificação Setor: {fmt_brl(sum(r['gratificacao'] for r in manicures))}</span>
    </div>

    <div class="box-info">
        <strong>Destaques do Setor:</strong> Com o fechamento do dia 31, todas as 3 manicures atingiram bonificação! <strong>Esmeralda</strong> fechou com R$ 17.930,00 (Nível Ouro - R$ 300,00). <strong>Safira</strong> superou a meta e bateu <strong>Nível Ouro</strong> com R$ 8.340,00 (R$ 300,00). <strong>Isaura</strong> superou a meta e bateu <strong>Nível Bronze</strong> com R$ 12.715,00 (R$ 150,00).
    </div>

    <table>
        <thead>
            <tr>
                <th style="width: 28%;">Manicure</th>
                <th style="width: 14%;">Faturamento Real</th>
                <th style="width: 28%;">Metas Individuais (B / P / O)</th>
                <th style="width: 10%;">Nível</th>
                <th style="width: 10%;">Gratificação</th>
                <th style="width: 10%;">Próxima Meta</th>
            </tr>
        </thead>
        <tbody>
"""
    for r in manicures:
        p = af._get_params_fat("manicures", mes, con, profissional=r["nome"])
        mb = fmt_brl(float(p['bronze_meta'])) if p and "bronze_meta" in p else "—"
        mp = fmt_brl(float(p['prata_meta'])) if p and "prata_meta" in p else "—"
        mo = fmt_brl(float(p['ouro_meta'])) if p and "ouro_meta" in p else "—"
        
        badge_cls = "badge-nenhum"
        if r.get("nivel") == "Ouro": badge_cls = "badge-ouro"
        elif r.get("nivel") == "Prata": badge_cls = "badge-prata"
        elif r.get("nivel") == "Bronze": badge_cls = "badge-bronze"

        nivel_label = r.get("nivel") or "—"
        fat_real = fmt_brl(r.get("faturamento"))
        grat = fmt_brl(r.get("gratificacao"))

        prox_str = "—"
        fat_val = r.get("faturamento") or 0.0
        if p and "ouro_meta" in p:
            v_b = float(p['bronze_meta'])
            v_p = float(p['prata_meta'])
            v_o = float(p['ouro_meta'])
            if fat_val >= v_o:
                prox_str = "<span style='color:#28a745; font-weight:600;'>★ Teto Atingido</span>"
            elif fat_val >= v_p:
                dif = v_o - fat_val
                prox_str = f"<span class='proxima-meta'>Ouro: falta <strong>{fmt_brl(dif)}</strong></span>"
            elif fat_val >= v_b:
                dif = v_p - fat_val
                prox_str = f"<span class='proxima-meta'>Prata: falta <strong>{fmt_brl(dif)}</strong></span>"
            else:
                dif = v_b - fat_val
                prox_str = f"<span class='proxima-meta'>Bronze: falta <strong>{fmt_brl(dif)}</strong></span>"

        metas_html = f"""
            <span class="faixa-meta"><span class="faixa-nome">B</span><span class="faixa-val">{mb}</span></span>
            <span class="faixa-meta"><span class="faixa-nome">P</span><span class="faixa-val">{mp}</span></span>
            <span class="faixa-meta"><span class="faixa-nome">O</span><span class="faixa-val">{mo}</span></span>
        """

        html += f"""
            <tr>
                <td class="nome-colaborador">{r['nome']}</td>
                <td><strong>{fat_real}</strong></td>
                <td>{metas_html}</td>
                <td><span class="badge-nivel {badge_cls}">{nivel_label}</span></td>
                <td><strong>{grat}</strong></td>
                <td>{prox_str}</td>
            </tr>
"""
    html += """
        </tbody>
    </table>

    <div class="tabela-premios">
        <span><strong>Valores de Bonificação Individual:</strong> Bronze: R$ 150,00 &nbsp;|&nbsp; Prata: R$ 200,00 &nbsp;|&nbsp; Ouro: R$ 300,00</span>
        <span>Metas individuais customizadas por profissional.</span>
    </div>
</div>

<!-- PÁGINA 3: ASSISTENTES & RECEPÇÃO (OUTUBRO) -->
<div class="pagina-setor">
    <div class="cabecalho">
        <h1>Gansos Barbearia</h1>
        <div class="mes">Apuração & Comissões — {mes} (Mês Completo Fechado)</div>
    </div>

    <div class="titulo-secao">
        <span>3. Assistentes & Recepção/Caixa — Apuração de Outubro/2026</span>
        <span class="badge-total-setor">Gratificação: {fmt_brl(sum(r['gratificacao'] for r in assistentes) + sum(r['gratificacao'] for r in recepcao))}</span>
    </div>

    <div class="painel-gate-titulo" style="margin-top:10px;">Setor de Assistentes (Serviços)</div>
    <table>
        <thead>
            <tr>
                <th style="width: 32%;">Assistente</th>
                <th style="width: 18%;">Faturamento Real</th>
                <th style="width: 25%;">Metas Gerais (B / P / O)</th>
                <th style="width: 12%;">Nível</th>
                <th style="width: 13%;">Gratificação</th>
            </tr>
        </thead>
        <tbody>
"""
    p_ast = af._get_params_fat("assistentes", mes, con)
    mb_ast = fmt_brl(float(p_ast['bronze_meta'])) if p_ast and "bronze_meta" in p_ast else "R$ 2.500,00"
    mp_ast = fmt_brl(float(p_ast['prata_meta'])) if p_ast and "prata_meta" in p_ast else "R$ 3.500,00"
    mo_ast = fmt_brl(float(p_ast['ouro_meta'])) if p_ast and "ouro_meta" in p_ast else "R$ 5.000,00"

    metas_ast_html = f"""
        <span class="faixa-meta"><span class="faixa-nome">B</span><span class="faixa-val">{mb_ast}</span></span>
        <span class="faixa-meta"><span class="faixa-nome">P</span><span class="faixa-val">{mp_ast}</span></span>
        <span class="faixa-meta"><span class="faixa-nome">O</span><span class="faixa-val">{mo_ast}</span></span>
    """

    for r in assistentes:
        badge_cls = "badge-nenhum"
        if r.get("nivel") == "Ouro": badge_cls = "badge-ouro"
        elif r.get("nivel") == "Prata": badge_cls = "badge-prata"
        elif r.get("nivel") == "Bronze": badge_cls = "badge-bronze"

        nivel_label = r.get("nivel") or "—"
        fat_real = fmt_brl(r.get("faturamento"))
        grat = fmt_brl(r.get("gratificacao"))

        html += f"""
            <tr>
                <td class="nome-colaborador">{r['nome']}</td>
                <td><strong>{fat_real}</strong></td>
                <td>{metas_ast_html}</td>
                <td><span class="badge-nivel {badge_cls}">{nivel_label}</span></td>
                <td><strong>{grat}</strong></td>
            </tr>
"""
    html += """
        </tbody>
    </table>

    <div class="painel-gate-titulo" style="margin-top:20px;">Setor de Recepção / Caixa (Produtos)</div>
"""
    if p_recep and "bronze_meta" in p_recep:
        rb = fmt_brl(float(p_recep['bronze_meta']))
        rp = fmt_brl(float(p_recep['prata_meta']))
        ro = fmt_brl(float(p_recep['ouro_meta']))
        premio_b = fmt_brl(float(p_recep.get('bronze_premio', 100)))
        premio_p = fmt_brl(float(p_recep.get('prata_premio', 175)))
        premio_o = fmt_brl(float(p_recep.get('ouro_premio', 250)))
        tot_recep = sum(r['faturamento'] for r in recepcao)

    html += f"""
    <table>
        <thead>
            <tr>
                <th style="width: 35%;">Equipe Recepção / Caixa</th>
                <th style="width: 25%;">Venda Individual</th>
                <th style="width: 25%;">Total Conjunto do Setor</th>
                <th style="width: 15%;">Gratificação</th>
            </tr>
        </thead>
        <tbody>
"""
    for r in recepcao:
        html += f"""
            <tr>
                <td class="nome-colaborador">{r['nome']}</td>
                <td>{fmt_brl(r['faturamento'])}</td>
                <td>{fmt_brl(r['total_setor'])}</td>
                <td><strong>{fmt_brl(r['gratificacao'])}</strong></td>
            </tr>
"""
    html += f"""
        </tbody>
    </table>

    <div class="tabela-premios">
        <span><strong>Premios:</strong> Assistentes: B R$ 150 / P R$ 225 / O R$ 300 &nbsp;|&nbsp; Recepção: B R$ 100 / P R$ 175 / O R$ 250 (cada)</span>
    </div>
</div>

<!-- PÁGINA 4: PROJEÇÃO DETALHADA BARBEIROS (NOVEMBRO/2026) -->
<div class="pagina-setor">
    <div class="cabecalho">
        <h1>Gansos Barbearia</h1>
        <div class="mes">Projeção & Metas Detalhadas — Novembro/2026</div>
    </div>

    <div class="titulo-secao">
        <span>4. Barbeiros — Metas Individuais de Ticket Médio (TM) para Novembro/2026</span>
        <span class="badge-total-setor">Vigência: 01/11/2026</span>
    </div>

    <div class="painel-gate">
        <div class="painel-gate-titulo">Gate Coletivo do Setor para Novembro (Base 3M: Ago R$ 86,8k + Set R$ 88,1k + Out R$ 132,4k)</div>
        <div class="gate-grid">
            <div class="gate-item">
                <div class="gate-label">Nova Base Média 3M</div>
                <div class="gate-val">R$ 102.445,67</div>
            </div>
            <div class="gate-item">
                <div class="gate-label">Bronze</div>
                <div class="gate-val">R$ 109.616,87</div>
            </div>
            <div class="gate-item">
                <div class="gate-label">Prata</div>
                <div class="gate-val">R$ 114.739,15</div>
            </div>
            <div class="gate-item ouro">
                <div class="gate-label">Ouro</div>
                <div class="gate-val">R$ 120.885,89</div>
            </div>
        </div>
        <div class="gate-obs">
            A base coletiva fechou em R$ 102.445,67 com a inclusão do mês completo de outubro (R$ 132.409 realizados). As metas individuais abaixo são válidas mediante o atingimento do faturamento coletivo mínimo (a partir do nível Bronze).
        </div>
    </div>

    <div style="background:#f8f9fa; border:1px solid #dfe3e8; border-radius:4px; padding:10px 18px; margin-bottom:12px; display:flex; justify-content:space-around; font-size:0.86em;">
        <span><strong>🟤 Bonificação Bronze:</strong> R$ 150,00</span>
        <span><strong>⚪ Bonificação Prata:</strong> R$ 300,00</span>
        <span><strong>🟡 Bonificação Ouro:</strong> R$ 500,00</span>
    </div>

    <table>
        <thead>
            <tr>
                <th style="width: 34%;">Barbeiro</th>
                <th style="width: 24%;">Base TM de Referência</th>
                <th style="width: 14%;">Meta Bronze</th>
                <th style="width: 14%;">Meta Prata</th>
                <th style="width: 14%;">Meta Ouro</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td class="nome-colaborador">Mateus Lima</td>
                <td>R$ 153,47</td>
                <td><strong>R$ 164,21</strong></td>
                <td><strong>R$ 171,89</strong></td>
                <td><strong>R$ 181,09</strong></td>
            </tr>
            <tr>
                <td class="nome-colaborador">Pedro Ian</td>
                <td>R$ 130,00</td>
                <td><strong>R$ 139,10</strong></td>
                <td><strong>R$ 145,60</strong></td>
                <td><strong>R$ 153,40</strong></td>
            </tr>
            <tr>
                <td class="nome-colaborador">William Silva Melo</td>
                <td>R$ 123,09</td>
                <td><strong>R$ 131,71</strong></td>
                <td><strong>R$ 137,86</strong></td>
                <td><strong>R$ 145,25</strong></td>
            </tr>
            <tr>
                <td class="nome-colaborador">Thiago Siqueira</td>
                <td>R$ 121,61</td>
                <td><strong>R$ 130,12</strong></td>
                <td><strong>R$ 136,20</strong></td>
                <td><strong>R$ 143,50</strong></td>
            </tr>
            <tr>
                <td class="nome-colaborador">Jose Erivelton Viana Leles</td>
                <td>R$ 113,90</td>
                <td><strong>R$ 121,87</strong></td>
                <td><strong>R$ 127,57</strong></td>
                <td><strong>R$ 134,40</strong></td>
            </tr>
            <tr>
                <td class="nome-colaborador">Davi Silva Martins</td>
                <td>R$ 112,58</td>
                <td><strong>R$ 120,46</strong></td>
                <td><strong>R$ 126,09</strong></td>
                <td><strong>R$ 132,84</strong></td>
            </tr>
            <tr>
                <td class="nome-colaborador">Ederson Duarte Carvalho</td>
                <td>R$ 111,65</td>
                <td><strong>R$ 119,47</strong></td>
                <td><strong>R$ 125,05</strong></td>
                <td><strong>R$ 131,75</strong></td>
            </tr>
            <tr>
                <td class="nome-colaborador">Caique Campos Ferreira</td>
                <td>R$ 105,74</td>
                <td><strong>R$ 113,14</strong></td>
                <td><strong>R$ 118,43</strong></td>
                <td><strong>R$ 124,77</strong></td>
            </tr>
        </tbody>
    </table>

    <div class="tabela-premios">
        <span>Metas individuais de Ticket Médio vigentes para Novembro/2026.</span>
    </div>
</div>

<!-- PÁGINA 5: PROJEÇÃO MANICURES, ASSISTENTES & RECEPÇÃO (NOVEMBRO/2026) -->
<div class="pagina-setor">
    <div class="cabecalho">
        <h1>Gansos Barbearia</h1>
        <div class="mes">Projeção & Metas Detalhadas — Novembro/2026</div>
    </div>

    <div class="titulo-secao">
        <span>5. Manicures, Assistentes & Recepção — Metas de Novembro/2026</span>
        <span class="badge-total-setor">Vigência: 01/11/2026</span>
    </div>

    <div class="painel-gate-titulo" style="margin-top:10px;">A. Setor de Manicures (Metas de Faturamento em Serviços)</div>

    <div style="background:#f8f9fa; border:1px solid #dfe3e8; border-radius:4px; padding:10px 18px; margin-bottom:12px; display:flex; justify-content:space-around; font-size:0.86em;">
        <span><strong>🟤 Bonificação Bronze:</strong> R$ 150,00</span>
        <span><strong>⚪ Bonificação Prata:</strong> R$ 200,00</span>
        <span><strong>🟡 Bonificação Ouro:</strong> R$ 300,00</span>
    </div>

    <table>
        <thead>
            <tr>
                <th style="width: 40%;">Manicure</th>
                <th style="width: 20%;">Meta Bronze</th>
                <th style="width: 20%;">Meta Prata</th>
                <th style="width: 20%;">Meta Ouro</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td class="nome-colaborador">Esmeralda Belém dos Santos</td>
                <td><strong>R$ 13.600,00</strong></td>
                <td><strong>R$ 15.000,00</strong></td>
                <td><strong>R$ 16.500,00</strong></td>
            </tr>
            <tr>
                <td class="nome-colaborador">Isaura Jéssica dos Santos Alves</td>
                <td><strong>R$ 12.300,00</strong></td>
                <td><strong>R$ 13.300,00</strong></td>
                <td><strong>R$ 14.350,00</strong></td>
            </tr>
            <tr>
                <td class="nome-colaborador">Rayssa Leite Da Silva Soares</td>
                <td><strong>R$ 10.150,00</strong></td>
                <td><strong>R$ 11.000,00</strong></td>
                <td><strong>R$ 11.850,00</strong></td>
            </tr>
            <tr>
                <td class="nome-colaborador">Safira Belém dos Santos</td>
                <td><strong>R$ 8.000,00</strong></td>
                <td><strong>R$ 8.700,00</strong></td>
                <td><strong>R$ 9.500,00</strong></td>
            </tr>
        </tbody>
    </table>

    <div class="painel-gate-titulo" style="margin-top:20px;">B. Setor de Assistentes (Tabela Progressiva por Faixa de Faturamento)</div>
    <table>
        <thead>
            <tr>
                <th style="width: 28%;">Faixa de Faturamento em Serviços</th>
                <th style="width: 22%;">Classificação</th>
                <th style="width: 28%;">Regra de Remuneração</th>
                <th style="width: 22%;">Gratificação Adicional</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>Abaixo de R$ 4.500,00</td>
                <td>Piso Padrão</td>
                <td>Comissão já acordada</td>
                <td><strong>—</strong></td>
            </tr>
            <tr>
                <td>R$ 4.500,00 a R$ 4.999,99</td>
                <td><span class="badge-nivel badge-bronze">Bronze</span></td>
                <td>Comissão acordada + Bônus</td>
                <td><strong>+ R$ 100,00</strong></td>
            </tr>
            <tr>
                <td>R$ 5.000,00 a R$ 5.999,99</td>
                <td><span class="badge-nivel badge-prata">Prata</span></td>
                <td>Comissão acordada + Bônus</td>
                <td><strong>+ R$ 200,00</strong></td>
            </tr>
            <tr>
                <td>R$ 6.000,00 a R$ 6.999,99</td>
                <td><span class="badge-nivel badge-ouro">Ouro</span></td>
                <td>Comissão acordada + Bônus</td>
                <td><strong>+ R$ 350,00</strong></td>
            </tr>
            <tr style="background-color: #e8f4fd;">
                <td><strong>A partir de R$ 7.000,00</strong></td>
                <td><span class="badge-nivel" style="background:#cce5ff; color:#004085; border:1px solid #b8daff;">Diamante 💎</span></td>
                <td>Comissão acordada + Bônus Máximo</td>
                <td><strong>+ R$ 500,00</strong></td>
            </tr>
        </tbody>
    </table>

    <div class="painel-gate-titulo" style="margin-top:20px;">C. Setor de Recepção / Caixa (Meta Coletiva de Produtos — Carol e Thamires)</div>
    <table>
        <thead>
            <tr>
                <th style="width: 34%;">Meta Geral Coletiva (Venda de Produtos)</th>
                <th style="width: 22%;">Bronze (R$ 5.000)</th>
                <th style="width: 22%;">Prata (R$ 7.000)</th>
                <th style="width: 22%;">Ouro (R$ 8.000)</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td><strong>Gratificação Individual para Cada uma</strong></td>
                <td><strong>R$ 100,00 cada</strong></td>
                <td><strong>R$ 175,00 cada</strong></td>
                <td><strong>R$ 250,00 cada</strong></td>
            </tr>
        </tbody>
    </table>

    <div class="tabela-premios" style="margin-top:16px;">
        <span><strong>Diretriz:</strong> Parâmetros oficiais cadastrados para vigência a partir de 01/11/2026.</span>
        <span>Gansos Hub — Plataforma de Gestão e Incentivos</span>
    </div>
</div>

</body>
</html>
"""
    with open(out_html, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Arquivo HTML gerado com sucesso: {out_html}")

if __name__ == "__main__":
    gerar_apuracao_doc()
