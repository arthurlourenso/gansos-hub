"""H5 — Faturamento mensal manicures e assistentes (RN-12/13), jan–jun/2026."""
import os
import sys

import pytest

ROOT_DIR = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, ROOT_DIR)
from src.apuracao_faturamento import apurar_faturamento

POLITICAS = ["manicures", "assistentes"]
MESES = ["2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06"]


def _por_nome(linhas: list[dict]) -> dict:
    return {r["nome"]: r["faturamento"] for r in linhas}


@pytest.mark.parametrize("politica", POLITICAS)
@pytest.mark.parametrize("mes", MESES)
def test_h5_faturamento_por_mes(con, golden, politica, mes):
    """Faturamento de cada profissional dentro da tolerância ±R$0,01."""
    tol = golden["H5"]["tolerancia"]
    ref = golden["H5"]["por_mes"][politica]
    linhas = apurar_faturamento(mes, politica, con)
    por_nome = _por_nome(linhas)

    erros = []
    for nome, meses_ref in ref.items():
        fat_esp = meses_ref[mes]
        fat_real = por_nome.get(nome, 0.0)
        if abs(fat_real - fat_esp) > tol:
            erros.append(
                f"{nome} ({politica}/{mes}): esperado R${fat_esp:.2f}, obtido R${fat_real:.2f}"
            )

    assert not erros, "\n".join(erros)


def test_h5_ana_mayra_excluida_apos_desligamento(con, golden):
    """Ana Mayra não deve aparecer na apuração de abr/2026 em diante (RN-13)."""
    linhas = apurar_faturamento("2026-08", "assistentes", con)
    nomes = [r["nome"] for r in linhas]
    assert "Ana Mayra Coelho De Jesus" not in nomes, (
        "Ana Mayra deveria estar excluída da apuração de 2026-08 (desligada em abr/2026)"
    )
