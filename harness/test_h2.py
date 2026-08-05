"""H2 — Ticket médio e elegibilidade de barbeiros (RN-10), jun+jul/2026."""
import os
import sys

import pytest

ROOT_DIR = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, ROOT_DIR)
from src.apuracao_barbeiros import apurar_barbeiros


def _por_nome(linhas: list[dict]) -> dict:
    return {r["nome"]: r for r in linhas}


@pytest.mark.parametrize("mes", ["2026-06", "2026-07"])
def test_h2_ticket_medio(con, golden, mes):
    """Ticket médio de cada barbeiro-alvo dentro da tolerância de ±R$0,05."""
    tol = golden["H2"]["tolerancia"]
    ref_mes = golden["H2"]["por_mes"][mes]
    linhas = apurar_barbeiros(mes, con)
    por_nome = _por_nome(linhas)

    erros = []
    for nome, ref in ref_mes.items():
        if nome not in por_nome:
            erros.append(f"{nome}: não encontrado na apuração de {mes}")
            continue
        tm_real = por_nome[nome]["ticket_medio"]
        tm_esp  = ref["ticket_medio"]
        if abs(tm_real - tm_esp) > tol:
            erros.append(
                f"{nome} ({mes}): TM esperado R${tm_esp:.2f}, obtido R${tm_real:.2f}"
            )

    assert not erros, "\n".join(erros)


@pytest.mark.parametrize("mes", ["2026-06", "2026-07"])
def test_h2_atendimentos(con, golden, mes):
    """Contagem de atendimentos únicos (data|cliente) por barbeiro-alvo."""
    ref_mes = golden["H2"]["por_mes"][mes]
    linhas = apurar_barbeiros(mes, con)
    por_nome = _por_nome(linhas)

    erros = []
    for nome, ref in ref_mes.items():
        if nome not in por_nome:
            erros.append(f"{nome}: não encontrado na apuração de {mes}")
            continue
        atend_real = por_nome[nome]["atendimentos"]
        atend_esp  = ref["atendimentos"]
        if atend_real != atend_esp:
            erros.append(
                f"{nome} ({mes}): atendimentos esperado {atend_esp}, obtido {atend_real}"
            )

    assert not erros, "\n".join(erros)


@pytest.mark.parametrize("mes", ["2026-06", "2026-07"])
def test_h2_elegibilidade(con, golden, mes):
    """Elegibilidade (>= 50 atendimentos) por barbeiro-alvo."""
    ref_mes = golden["H2"]["por_mes"][mes]
    linhas = apurar_barbeiros(mes, con)
    por_nome = _por_nome(linhas)

    erros = []
    for nome, ref in ref_mes.items():
        if nome not in por_nome:
            erros.append(f"{nome}: não encontrado na apuração de {mes}")
            continue
        elig_real = por_nome[nome]["elegivel"]
        elig_esp  = ref["elegivel"]
        if elig_real != elig_esp:
            erros.append(
                f"{nome} ({mes}): elegivel esperado {elig_esp}, obtido {elig_real}"
            )

    assert not erros, "\n".join(erros)


@pytest.mark.parametrize("mes", ["2026-06", "2026-07"])
def test_h2_nivel(con, golden, mes):
    """Nível de gratificação (Bronze/Prata/Ouro/None) por barbeiro-alvo."""
    ref_mes = golden["H2"]["por_mes"][mes]
    linhas = apurar_barbeiros(mes, con)
    por_nome = _por_nome(linhas)

    erros = []
    for nome, ref in ref_mes.items():
        if nome not in por_nome:
            erros.append(f"{nome}: não encontrado na apuração de {mes}")
            continue
        nivel_real = por_nome[nome]["nivel"]
        nivel_esp  = ref["nivel"]
        if nivel_real != nivel_esp:
            erros.append(
                f"{nome} ({mes}): nivel esperado {nivel_esp!r}, obtido {nivel_real!r}"
            )

    assert not erros, "\n".join(erros)


def test_h2_thiago_inelegivel_ambos_meses(con, golden):
    """Thiago Siqueira deve ser inelegível em jun e jul (< 50 atendimentos)."""
    nome = "Thiago Siqueira"
    for mes in ["2026-06", "2026-07"]:
        linhas = apurar_barbeiros(mes, con)
        por_nome = _por_nome(linhas)
        assert nome in por_nome, f"Thiago não encontrado na apuração de {mes}"
        assert not por_nome[nome]["elegivel"], (
            f"Thiago Siqueira deveria ser INELEGIVEL em {mes} "
            f"(atend={por_nome[nome]['atendimentos']})"
        )
