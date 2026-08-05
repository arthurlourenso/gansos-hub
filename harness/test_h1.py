"""H1 — Volume de produtos (7 arquivos mensais)."""
import pytest


def test_h1_total_linhas(con, golden):
    esperado = golden["H1"]["total_linhas"]
    atual = con.execute("SELECT COUNT(*) FROM vendas WHERE tipo='Produto'").fetchone()[0]
    assert atual == esperado, f"Linhas de produtos: esperado {esperado}, obtido {atual}"


def test_h1_total_valor(con, golden):
    esperado = golden["H1"]["total_valor"]
    atual = con.execute("SELECT ROUND(SUM(valor), 2) FROM vendas WHERE tipo='Produto'").fetchone()[0]
    assert atual == pytest.approx(esperado, abs=0.01), (
        f"Soma produtos: esperado R$ {esperado:,.2f}, obtido R$ {atual:,.2f}"
    )


def test_h1_por_mes(con, golden):
    rows = con.execute("""
        SELECT strftime('%Y-%m', data_hora) as mes, COUNT(*), ROUND(SUM(valor), 2)
        FROM vendas WHERE tipo='Produto'
        GROUP BY mes ORDER BY mes
    """).fetchall()
    por_mes = {r[0]: {"linhas": r[1], "valor": r[2]} for r in rows}

    for mes, ref in golden["H1"]["por_mes"].items():
        assert mes in por_mes, f"Mês {mes} não encontrado no banco"
        assert por_mes[mes]["linhas"] == ref["linhas"], (
            f"{mes}: linhas esperado {ref['linhas']}, obtido {por_mes[mes]['linhas']}"
        )
        assert por_mes[mes]["valor"] == pytest.approx(ref["valor"], abs=0.01), (
            f"{mes}: valor esperado R$ {ref['valor']:,.2f}, obtido R$ {por_mes[mes]['valor']:,.2f}"
        )


def test_h1_zero_valores_nulos(con, golden):
    nulos = con.execute(
        "SELECT COUNT(*) FROM vendas WHERE tipo='Produto' AND valor IS NULL"
    ).fetchone()[0]
    assert nulos == 0, f"{nulos} linha(s) com valor NULL em produtos"


def test_h1_zero_datas_invalidas(con, golden):
    invalidas = con.execute("""
        SELECT COUNT(*) FROM vendas
        WHERE tipo='Produto'
          AND (data_hora IS NULL
               OR data_hora NOT GLOB '????-??-?? ??:??:??')
    """).fetchone()[0]
    assert invalidas == 0, f"{invalidas} linha(s) com data inválida em produtos"
