"""
src/ingestao.py — Importador unificado de exports do AppBarber.
Uso: python src/ingestao.py <arquivo.xlsx>
"""
import argparse
import io
import os
import sys
import zipfile
from datetime import datetime

import src.db as db

# Minimal styles.xml: openpyxl rejects files with fills malformados
_STYLES_MINIMAL = b"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <fonts><font><sz val="11"/><name val="Calibri"/></font></fonts>
  <fills>
    <fill><patternFill patternType="none"/></fill>
    <fill><patternFill patternType="gray125"/></fill>
  </fills>
  <borders><border><left/><right/><top/><bottom/><diagonal/></border></borders>
  <cellStyleXfs count="1">
    <xf numFmtId="0" fontId="0" fillId="0" borderId="0"/>
  </cellStyleXfs>
  <cellXfs>
    <xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>
  </cellXfs>
  <cellStyles>
    <cellStyle name="Normal" xfId="0" builtinId="0"/>
  </cellStyles>
</styleSheet>"""


def _fix_styles(path: str) -> io.BytesIO:
    buf = io.BytesIO()
    with zipfile.ZipFile(path, "r") as zin, zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = _STYLES_MINIMAL if item.filename == "xl/styles.xml" else zin.read(item.filename)
            zout.writestr(item, data)
    buf.seek(0)
    return buf


def _abrir_xlsx(path: str):
    import openpyxl
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            return openpyxl.load_workbook(path, read_only=True, data_only=True)
        except Exception:
            return openpyxl.load_workbook(_fix_styles(path), read_only=True, data_only=True)


def _norm_col(nome: str) -> str:
    import unicodedata
    s = unicodedata.normalize("NFD", str(nome).lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn").strip()


def _parse_valor(v) -> float | None:
    if v is None:
        return None
    s = str(v).replace("R$", "").replace(".", "").replace(",", ".").strip()
    try:
        return float(s)
    except ValueError:
        return None


def _parse_data(v) -> str | None:
    if v is None:
        return None
    s = str(v).strip()
    for fmt in ("%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y"):
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
    return None


# Colunas obrigatórias por layout
_COLS_PRODUTOS = {"data", "valor", "tipo", "item", "profissional", "cliente"}
_COLS_SERVICOS = {"data", "valor", "tipo", "item", "profissional", "cliente"}


def _detectar_layout(cabecalho: list[str]) -> str:
    presentes = {_norm_col(c) for c in cabecalho if c}
    if _COLS_PRODUTOS <= presentes:
        return "produtos"
    raise ValueError(
        f"Layout não reconhecido. Colunas encontradas: {cabecalho}\n"
        "Esperado: Data, Valor, Tipo, Item, Profissional, Cliente (+ opcional Comissão)."
    )


def _get_ou_criar_profissional(con, nome: str) -> int | None:
    if not nome:
        return None
    nome = nome.strip()
    if not nome:
        return None
    row = con.execute("SELECT id FROM profissionais WHERE nome_sistema = ?", (nome,)).fetchone()
    if row:
        return row[0]
    cur = con.execute(
        "INSERT INTO profissionais (nome_sistema, funcao, ativo) VALUES (?, 'pendente', 1)", (nome,)
    )
    return cur.lastrowid


def importar(path: str, con) -> dict:
    arquivo_origem = os.path.basename(path)
    importado_em = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Dedup por arquivo: se já foi importado, nada entra
    ja_importado = con.execute(
        "SELECT COUNT(*) FROM vendas WHERE arquivo_origem = ?", (arquivo_origem,)
    ).fetchone()[0]
    if ja_importado:
        return {"lidas": 0, "inseridas": 0, "duplicadas": ja_importado, "rejeitadas": 0, "rejeicoes": []}

    wb = _abrir_xlsx(path)
    ws = wb.active
    todas = list(ws.iter_rows(min_row=1, values_only=True))
    wb.close()

    if not todas:
        return {"lidas": 0, "inseridas": 0, "duplicadas": 0, "rejeitadas": 0, "rejeicoes": []}

    cabecalho_raw = [str(c) if c is not None else "" for c in todas[0]]
    _detectar_layout(cabecalho_raw)  # valida antes de processar
    col = {_norm_col(nome): i for i, nome in enumerate(cabecalho_raw)}

    lidas = inseridas = duplicadas = 0
    rejeicoes: list[tuple[int, str]] = []

    for linha_num, row in enumerate(todas[1:], start=2):
        # Pula rodapé Total: e linhas completamente vazias
        primeira = str(row[0]).strip() if row[0] is not None else ""
        if not primeira or primeira.lower().startswith("total"):
            continue

        tipo = str(row[col["tipo"]]).strip() if row[col["tipo"]] is not None else ""
        if not tipo:
            continue

        lidas += 1

        data_hora = _parse_data(row[col["data"]])
        if data_hora is None:
            rejeicoes.append((linha_num, f"data inválida: {row[col['data']]!r}"))
            continue

        valor = _parse_valor(row[col["valor"]])
        if valor is None:
            rejeicoes.append((linha_num, f"valor inválido: {row[col['valor']]!r}"))
            continue

        item = str(row[col["item"]]).strip() if row[col["item"]] is not None else ""
        profissional_nome = str(row[col["profissional"]]).strip() if row[col["profissional"]] is not None else ""
        cliente = str(row[col["cliente"]]).strip() if row[col.get("cliente")] is not None else ""
        comissao = _parse_valor(row[col["comissao"]]) if "comissao" in col else None

        profissional_id = _get_ou_criar_profissional(con, profissional_nome)

        con.execute(
            """INSERT INTO vendas
               (data_hora, valor, tipo, item, profissional_id, cliente,
                comissao_sistema, arquivo_origem, importado_em)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (data_hora, valor, tipo, item, profissional_id, cliente,
             comissao, arquivo_origem, importado_em),
        )
        inseridas += 1

    return {
        "lidas": lidas,
        "inseridas": inseridas,
        "duplicadas": duplicadas,
        "rejeitadas": len(rejeicoes),
        "rejeicoes": rejeicoes,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Importa um export .xlsx do AppBarber.")
    parser.add_argument("arquivo", help="Caminho para o arquivo .xlsx")
    args = parser.parse_args()

    path = args.arquivo
    if not os.path.exists(path):
        print(f"Arquivo não encontrado: {path}", file=sys.stderr)
        sys.exit(1)

    with db.conectar() as con:
        resultado = importar(path, con)

    r = resultado
    print(f"\nImportação: {os.path.basename(path)}")
    print(f"  Lidas:      {r['lidas']:>6}")
    print(f"  Inseridas:  {r['inseridas']:>6}")
    print(f"  Duplicadas: {r['duplicadas']:>6}")
    print(f"  Rejeitadas: {r['rejeitadas']:>6}")

    if r["rejeicoes"]:
        print("\nLinhas rejeitadas:")
        for ln, motivo in r["rejeicoes"]:
            print(f"  linha {ln}: {motivo}")

    if r["rejeitadas"] > 0:
        sys.exit(2)


if __name__ == "__main__":
    main()
