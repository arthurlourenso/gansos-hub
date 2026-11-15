# 05 — Gansos Hub online (Supabase + Streamlit)

Plano para publicar o Hub na internet, mantendo o Streamlit atual e trocando o
banco local (SQLite) por um Postgres gerenciado (Supabase). Documento vivo —
atualizar à medida que cada fase é executada.

## 1. Objetivo
Sair de "roda só na máquina do Arthur" para "acessível pela web por você e pela
gerência", sem reescrever a aplicação e sem alterar nenhum número de apuração.

## 2. Decisões (15/11/2026)
- **D-ON-1 — Caminho A (manter Streamlit).** O app continua em Streamlit; só o
  banco migra para o Supabase. Rework mínimo, aproveita 100% do código atual.
  Vercel exigiria reescrever a interface em Next.js (Caminho B) — fica como
  evolução futura, não agora. O Supabase e a apuração montados aqui servem aos
  dois caminhos.
- **D-ON-2 — Público: você + gerência.** Poucos gestores de confiança veem tudo.
  Profissionais **não** acessam nesta versão (isso exigiria filtragem por pessoa).
- **D-ON-3 — Login por usuário.** Cada gestor com usuário/senha próprios (não
  senha compartilhada). Biblioteca a confirmar na Fase 3 (streamlit-authenticator,
  mais simples para poucos usuários, vs Supabase Auth, unificado com o banco).
- **D-ON-4 — Hospedagem a confirmar na Fase 5:** Streamlit Community Cloud
  (grátis, deploy do GitHub, secrets nativos, URL pública) é o default; container
  pago (Render/Railway) se quisermos domínio próprio ou rede restrita.

## 3. Estado atual (já pronto — commit T9)
- `src/db.py`: troca SQLite ↔ Postgres por `DATABASE_URL`, converte `?`→`%s`,
  tem `mes_expr`/`date_expr` por dialeto. **Toda a apuração é dialect-agnostic.**
- `db/schema_pg.sql`: schema Postgres completo e alinhado ao SQLite atual.
- `psycopg2-binary` já em `requirements.txt`.
- `.streamlit/secrets.toml` e dados sensíveis (`db/`, `dados/entrada/`) já no
  `.gitignore`.
- Volume a migrar: ~25k vendas, 40 profissionais, 79 parâmetros, 1 apuração.

## 4. Falta fazer
Migração dos dados · validação contra Postgres · **autenticação (inexistente)** ·
ingestão de xlsx por upload (hoje é CLI local) · deploy.

## 5. Fases

### F0 — Preparação (ação do Arthur)
- Criar projeto no Supabase (região São Paulo).
- Pegar a string do **pooler** (porta 6543, modo transaction), não a conexão
  direta — app hospedado esgota conexões diretas.
- Guardar a string em `.streamlit/secrets.toml` (nunca no chat nem no git).
- **CP:** `DATABASE_URL` disponível localmente via secrets.

### F1 — Dados no Supabase ✅ CONCLUÍDA (15/11/2026)
- Projeto Supabase: `Gansos-hub` (ref esxutwjuhxceyncjmdwq), região us-east-2.
- Schema criado via MCP; profissionais (40), parâmetros (79) e apurações (1)
  migrados via MCP; vendas (25.009, soma R$2.341.797,01) via
  `scripts/migrar_vendas_supabase.py` (psycopg2). Contagens batem.
- **Validação:** harness roda nos dois bancos com resultado idêntico — todas as
  apurações (H2 barbeiros, H5 manicures/assistentes, H6 modelo setor+TM) passam
  no Supabase. **A migração não mudou nenhum número.**
- **Correções de portabilidade descobertas (beneficiam o app, não só o teste):**
  - `db.py`: NUMERIC do Postgres agora volta como `float` (igual ao REAL do
    SQLite) — senão `SUM(valor)` divergia por tipo (Decimal vs float).
  - `db.py`: `execute` dá rollback no erro. No Postgres uma query com erro
    abortava a conexão em cache e travava o app todo até reiniciar.
  - Harness (H1/H4/H6) deixado dialect-portável (`mes_expr`, sem `strftime`/
    `GLOB`/`json_extract` cravados; testes de lógica SQLite in-memory pulam no PG).
- **Pendência conhecida (NÃO é da migração):** `test_h1_total_linhas/valor`
  falham nos dois bancos — o golden de volume está congelado em jan–ago/2026 e os
  dados já vão até novembro. Refrescar esse golden é tarefa à parte.
- **Reversível:** nada apagou o SQLite local.

### F2 — App contra o Supabase ✅ CONCLUÍDA (15/11/2026)
- `db.py` resolve a conexão assim: env var `DATABASE_URL` → `st.secrets` **só
  quando rodando dentro do app Streamlit** (`streamlit.runtime.exists()`) →
  SQLite. Scripts/harness seguem em SQLite; o app usa Supabase.
- Testado local: todas as abas (Vendas, Apuração dos 4 setores, Parâmetros,
  Análise Individual) renderizam contra o Supabase, sem erro de console nem de
  servidor. Dados conferem (mês 2026-11, última venda 12/11).
- **Risco do pooler resolvido:** o Streamlit mantém uma conexão persistente
  (`@st.cache_resource`), então o **Session pooler (5432)** é o certo — aguentou
  muitos reruns e queries sem cair. O Transaction pooler (6543) só faria sentido
  em serverless. O rollback-no-erro (F1) protege a conexão em cache de travar.
- **CP cumprido:** dashboard funciona contra o Supabase sem erro.

### F3 — Autenticação (bloqueante — sem isso não sobe)
- Gate de login: nada renderiza sem autenticar.
- Chave do banco só nos secrets do servidor, nunca no front.
- Usuários da gerência com senha hash nos secrets (ou Supabase Auth).
- **Risco:** URL pública → o gate é o que protege o dado salarial.
- **CP:** sem login válido, nenhuma aba aparece.

### F4 — Ingestão online
- `st.file_uploader` numa aba de admin protegida, chamando `ingestao.importar()`.
  Dedup por `arquivo_origem` já cobre reenvio.
- **CP:** importar um export do AppBarber pela web atualiza o banco.

### F5 — Deploy e operação
- Confirmar que dados sensíveis seguem fora do git (já estão).
- Conectar o repo ao host escolhido (D-ON-4) e configurar secrets lá.
- Harness no CI a cada push: nenhuma mudança quebra os números em silêncio.
- **Reversibilidade:** SQLite local segue como fonte de verdade/backup até
  confiarmos no online.
- **CP:** você e a gerência acessam pela web, com login, contra o Supabase.

## 6. Ordem de execução
F0 (você) → F1 → F2 → F3 → F4 → F5. F1 e F2 são reversíveis e não afetam o uso
local atual; o "go live" real só na F5, depois da F3.

## 7. Pendências
- **Driver psycopg2 → psycopg3.** O `psycopg2-binary==2.9.10` não tem wheel para
  Python 3.14, e o build do Community Cloud quebra (precisa compilar, sem
  `pg_config`). Contorno atual: fixar Python 3.13 nas settings do app. Correção
  definitiva: migrar `db.py` para `psycopg` (psycopg3), que tem wheel p/ 3.14,
  removendo a dependência da versão do Python. Pequena mudança + teste local
  contra o Supabase.
- **F3 — Autenticação por código** (login por usuário, você + gerência). Deixada
  por último a pedido; no interim, o app sobe **privado** no Community Cloud
  (acesso só por e-mail convidado). Candidato: `streamlit-authenticator`.
- **Refrescar o golden do H1** (`golden_numbers.json`). Está congelado em
  jan–ago/2026 (989 produtos); os dados já vão até novembro, então
  `test_h1_total_linhas/valor` falham nos dois bancos. Atualizar para o CI (F5)
  ficar verde.
- **Front/responsividade** — em andamento por você via Antigravity.
