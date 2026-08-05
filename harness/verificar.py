"""
harness/verificar.py — Executor do harness Gansos Hub.
Uso: python harness/verificar.py
Roda todos os checks disponíveis e exibe resumo. Exit 0 = tudo verde.
"""
import json
import os
import subprocess
import sys

HARNESS_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(HARNESS_DIR)
GOLDEN_PATH = os.path.join(HARNESS_DIR, "golden_numbers.json")
DB_PATH = os.path.join(ROOT_DIR, "db", "gansos.db")


def _carregar_golden() -> dict:
    with open(GOLDEN_PATH, encoding="utf-8") as f:
        return json.load(f)


def _pendentes(golden: dict) -> list[str]:
    return [k for k, v in golden.items() if isinstance(v, dict) and v.get("status", "").startswith("pendente")]


def main() -> int:
    print("=" * 60)
    print("  HARNESS - Gansos Hub")
    print("=" * 60)

    if not os.path.exists(DB_PATH):
        print(f"\n[ERRO] Banco não encontrado: {DB_PATH}")
        print("       Rode: python init_db.py && python src/ingestao.py <arquivo>")
        return 1

    golden = _carregar_golden()
    pendentes = _pendentes(golden)
    if pendentes:
        print(f"\nChecks pendentes (aguardam tasks futuras): {', '.join(pendentes)}")

    print("\nRodando pytest...\n")

    resultado = subprocess.run(
        [sys.executable, "-m", "pytest", HARNESS_DIR, "-v", "--tb=short", "--no-header"],
        cwd=ROOT_DIR,
    )

    print("\n" + "=" * 60)
    if resultado.returncode == 0:
        print("  RESULTADO: TUDO VERDE [OK]")
    else:
        print("  RESULTADO: FALHAS DETECTADAS [FAIL]")
    print("=" * 60)

    return resultado.returncode


if __name__ == "__main__":
    sys.exit(main())
