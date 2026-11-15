"""H6 — RN-10 v2: gate coletivo do setor + TM individual (vigência set/2026)."""
import os
import sqlite3
import sys

import pytest

ROOT_DIR = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, ROOT_DIR)
import src.db as db
from src.apuracao_barbeiros import apurar_barbeiros, resumo_setor, seed_parametros_v2


def _por_nome(linhas):
    return {r["nome"]: r for r in linhas}


# ---------------------------------------------------------------------------
# Setembro/2026 real (fechado, 24 dias com movimento)
# ---------------------------------------------------------------------------

def test_h6_setor_setembro_nao_abre_nivel(con):
    s = resumo_setor("2026-09", con)
    assert s["faturamento"] == pytest.approx(88078.0, abs=0.01)
    assert s["base"] == pytest.approx(88471.0, abs=0.01)
    assert s["nivel"] is None
    assert s["metas"]["Bronze"] == pytest.approx(94663.97, abs=0.01)


def test_h6_setembro_ninguem_recebe(con):
    linhas = apurar_barbeiros("2026-09", con)
    assert sum(r["gratificacao"] for r in linhas) == 0.0


def test_h6_setembro_niveis_tm(con):
    por = _por_nome(apurar_barbeiros("2026-09", con))
    mateus = por["Mateus  Lima"]
    assert mateus["tm_base"] == pytest.approx(149.85, abs=0.05)
    assert mateus["nivel_tm"] == "Bronze"
    assert mateus["nivel"] is None  # setor sem nível trava o bônus
    assert por["Thiago Siqueira"]["nivel_tm"] == "Ouro"
    assert por["Thiago Siqueira"]["baseline_meses"] == 3
    assert por["William Silva Melo"]["nivel_tm"] is None


def test_h6_getulio_fora_das_analises(con):
    nomes = {r["nome"] for r in apurar_barbeiros("2026-09", con)}
    assert "Getúlio Silva Do Nascimento Junior" not in nomes


def test_h6_pdi_meta_atendimentos(con):
    por = _por_nome(apurar_barbeiros("2026-09", con))
    assert por["William Silva Melo"]["pdi_meta"] == 233
    assert por["Thiago Siqueira"]["pdi_atingiu"] is True
    assert por["Jose Erivelton Viana Leles"]["pdi_atingiu"] is False


def test_h6_agosto_segue_regua_antiga(con):
    """RN-21: mês anterior à vigência v2 não muda."""
    por = _por_nome(apurar_barbeiros("2026-08", con))
    assert por["Mateus  Lima"]["modelo"] == "legado"
    assert por["Mateus  Lima"]["gratificacao"] == 500.0
    assert por["William Silva Melo"]["gratificacao"] == 150.0
    assert resumo_setor("2026-08", con) is None


# ---------------------------------------------------------------------------
# Regra min(setor, TM) com dados sintéticos
# ---------------------------------------------------------------------------

def _con_sintetica(tm_a_set: float, tm_b_set: float):
    raw = sqlite3.connect(":memory:")
    raw.row_factory = sqlite3.Row
    raw.executescript("""
        CREATE TABLE profissionais (id INTEGER PRIMARY KEY, nome_sistema TEXT UNIQUE,
                                    funcao TEXT, ativo INTEGER DEFAULT 1);
        CREATE TABLE vendas (id INTEGER PRIMARY KEY, data_hora TEXT, valor REAL, tipo TEXT,
                             item TEXT, profissional_id INTEGER, cliente TEXT,
                             comissao_sistema REAL, arquivo_origem TEXT, importado_em TEXT);
        CREATE TABLE parametros (id INTEGER PRIMARY KEY, politica TEXT, chave TEXT, valor TEXT,
                                 vigencia_inicio TEXT, vigencia_fim TEXT, alterado_por TEXT,
                                 alterado_em TEXT, profissional TEXT);
    """)
    raw.execute("INSERT INTO profissionais (id, nome_sistema, funcao) VALUES (1,'A','barbeiro'),(2,'B','barbeiro')")
    tms = {"2026-06": (100, 100), "2026-07": (100, 100), "2026-08": (100, 100),
           "2026-09": (tm_a_set, tm_b_set)}
    for mes, (ta, tb) in tms.items():
        for pid, tm in ((1, ta), (2, tb)):
            for i in range(1, 11):
                raw.execute(
                    "INSERT INTO vendas (data_hora, valor, tipo, item, profissional_id, cliente,"
                    " arquivo_origem, importado_em) VALUES (?,?,?,?,?,?,?,?)",
                    (f"{mes}-{i:02d} 10:00:00", tm, "Serviço", "Corte", pid, f"c{i}", "t", "t"),
                )
    con = db.Connection(raw, is_pg=False)
    seed_parametros_v2(con)
    return con


@pytest.mark.skipif(db.dialect() == "postgres", reason="lógica em SQLite in-memory; validada na rodada SQLite")
def test_h6_efetivo_e_o_menor_entre_setor_e_tm():
    # A +20% (Ouro de TM), B +8% (Bronze de TM) → setor +14% = Prata
    con = _con_sintetica(120, 108)
    assert resumo_setor("2026-09", con)["nivel"] == "Prata"
    por = _por_nome(apurar_barbeiros("2026-09", con))
    assert por["A"]["nivel_tm"] == "Ouro" and por["A"]["nivel"] == "Prata"
    assert por["A"]["gratificacao"] == 300.0
    assert por["B"]["nivel_tm"] == "Bronze" and por["B"]["nivel"] == "Bronze"
    assert por["B"]["gratificacao"] == 150.0


@pytest.mark.skipif(db.dialect() == "postgres", reason="lógica em SQLite in-memory; validada na rodada SQLite")
def test_h6_tm_ouro_com_setor_bronze_paga_bronze():
    # A +20%, B 0% → setor +10% = Bronze; A tem TM Ouro mas recebe Bronze
    con = _con_sintetica(120, 100)
    assert resumo_setor("2026-09", con)["nivel"] == "Bronze"
    por = _por_nome(apurar_barbeiros("2026-09", con))
    assert por["A"]["nivel_tm"] == "Ouro"
    assert por["A"]["gratificacao"] == 150.0
    assert por["B"]["nivel"] is None and por["B"]["gratificacao"] == 0.0


@pytest.mark.skipif(db.dialect() == "postgres", reason="lógica em SQLite in-memory; validada na rodada SQLite")
def test_h6_setor_sem_crescimento_trava_todos():
    # A +20%, B −15% → setor +2,5% (< Bronze): ninguém recebe, mesmo com TM Ouro
    con = _con_sintetica(120, 85)
    assert resumo_setor("2026-09", con)["nivel"] is None
    assert all(r["gratificacao"] == 0.0 for r in apurar_barbeiros("2026-09", con))
