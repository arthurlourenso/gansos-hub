# Gansos Hub

Plataforma local de dados e incentivos — Gansos Barbearia.
Base unificada (SQLite) + dashboard (Streamlit) + apuração mensal de gratificações.

---

## Pré-requisitos

- Python 3.12 instalado
- Dependências: `pip install streamlit openpyxl pandas`

## Primeira vez (setup)

```bash
cd C:\Users\arthu\.gansos-hub
python init_db.py
```

---

## Ciclo mensal

### 1. Exportar do AppBarber

No AppBarber, gere dois exports e salve em `dados/entrada/`:

| Export | Arquivo gerado | Tipo |
|---|---|---|
| Relatório de serviços (mês completo) | `ex: julho-servicos.xlsx` | Serviços |
| Relatório de produtos (mês) | `ex: julho-26.xlsx` | Produtos |

### 2. Importar

Execute um arquivo por vez. O comando detecta o layout automaticamente:

```bash
python src/ingestao.py dados/entrada/julho-26.xlsx
python src/ingestao.py dados/entrada/julho-servicos.xlsx
```

O relatório exibe: `lidas / inseridas / duplicadas / rejeitadas`.
Reimportar o mesmo arquivo é seguro — retorna 0 inseridas.

### 3. Conferir pendentes

Profissionais sem função classificada aparecem como `pendente` e são ignorados na apuração.
Verifique no banco se surgiram nomes novos:

```bash
python -c "
import sqlite3
con = sqlite3.connect('db/gansos.db')
rows = con.execute(\"SELECT nome_sistema FROM profissionais WHERE funcao='pendente'\").fetchall()
for r in rows: print(r[0])
"
```

Se houver novos, classifique manualmente editando `src/apuracao_barbeiros.py` (lista `BARBEIROS`)
ou `src/apuracao_faturamento.py` (listas `MANICURES` / `ASSISTENTES`) e rode o seed:

```bash
python src/apuracao_barbeiros.py --seed 2026-07
python src/apuracao_faturamento.py --seed 2026-07 manicures
```

### 4. Abrir o dashboard

```bash
python -m streamlit run src/dashboard.py
```

Acesse **http://localhost:8501** no navegador.

### 5. Apurar e publicar

Na aba **📋 Apuração**, selecione o mês no menu lateral e revise:

- **Barbeiros** — ticket médio × metas Bronze/Prata/Ouro (RN-10)
- **Manicures** — faturamento × metas (RN-12)
- **Assistentes** — faturamento × metas (RN-13)

Quando os números estiverem corretos, clique em **Publicar apuração** por política.
Após publicar, o snapshot fica imutável — mudanças futuras de parâmetros não afetam meses publicados.

### 6. Alterar metas (quando necessário)

Na aba **⚙️ Parâmetros**, expanda a política desejada, preencha os novos valores
e defina a **Vigência a partir de** (ex: `2026-10-01` para valer a partir de outubro).
A vigência anterior é fechada automaticamente.

---

## Verificação de integridade

```bash
python harness/verificar.py
```

Todos os checks devem estar verdes antes de publicar.

---

## Estrutura

```
gansos-hub/
├── src/
│   ├── ingestao.py              # importação de exports xlsx
│   ├── apuracao_barbeiros.py    # RN-10: ticket médio
│   ├── apuracao_faturamento.py  # RN-12/13: manicures e assistentes
│   └── dashboard.py             # Streamlit (4 abas)
├── harness/                     # testes automatizados
├── db/gansos.db                 # banco (não versionado)
├── dados/entrada/               # exports xlsx (não versionados)
└── docs/                        # spec, plan e tasks
```
