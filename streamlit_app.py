"""Entrypoint do app para o Streamlit Community Cloud.

O Community Cloud roda o script a partir da própria pasta (src/), então
`import src.db` não encontra o pacote `src`. Este arquivo na raiz garante o
repo root no sys.path e chama o dashboard. Localmente continua funcionando
tanto por aqui quanto por `streamlit run src/dashboard.py`.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.dashboard import main

main()
