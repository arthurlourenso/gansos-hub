# TASKS — Gansos Hub
Executar UMA por vez. Ao fim de cada: rodar o harness e colar a saída. CP = critério de pronto.

## T1 — Esqueleto + banco
Criar estrutura da §1 do PLAN, `schema.sql` com as tabelas da §2, script `init_db.py`,
git inicializado, `.gitignore` (db, dados/entrada, __pycache__).
**CP:** `init_db.py` cria o banco do zero; harness "estrutura" verde.

## T2 — Ingestão unificada
`src/ingestao.py <arquivo.xlsx>`: detecta o layout, corrige styles.xml, normaliza, deduplica,
insere, imprime o relatório de import (RN-31). Profissionais novos → 'pendente'.
**CP:** importar os 7 mensais de produtos + o export geral de serviços sem erro; harness
"golden numbers de volume" verde.

## T3 — Harness completo
Implementar `harness/verificar.py` + pytest com os números de 04-HARNESS.md.
**CP:** todos os checks rodam num comando; falha de propósito (alterar um número) é detectada.

## T4 — Apuração barbeiros (F2)
`apurar_barbeiros(mes)` conforme RN-10, lendo parâmetros com vigência. Seed de parâmetros:
metas/prêmios/mínimo atuais com vigência 2026-08-01.
**CP:** retroativo jun e jul/2026 bate com os golden numbers de ticket médio; caso
"abaixo do mínimo" demonstrado.

## T5 — Apuração produtos (F3; após decisões D1 da SPEC)
`apurar_produtos(mes)` conforme spec sdd-comissionamento (categorização §3 de lá inclusa).
**CP:** retroativo jan–jul bate com golden numbers de produtos; guardrail calculado.

## T5b — Apuração manicures e assistentes (F4)
`apurar_faturamento(mes, politica)` genérica para RN-12 e RN-13: soma faturamento mensal
por profissional da função, aplica a régua vigente. Seed de parâmetros com vigência 2026-08-01.
**CP:** retroativo jan–jun bate com golden numbers H5; Raynara ausente de apurações ≥ ago/26.

## T6 — Dashboard
As 4 abas da §5 do PLAN, lendo só do banco.
**CP:** CA-2 da SPEC demonstrado com dados reais; não-técnico navega sem instrução.

## T7 — Painel de parâmetros + publicação
Edição com vigência e trilha de alteração; publicação de apuração (snapshot imutável).
**CP:** CA-4 demonstrado: mudar meta → mês seguinte muda, mês publicado não.

## T8 — README + fluxo mensal
Documentar o ciclo: exportar do AppBarber → importar → conferir pendentes → apurar →
publicar. Máx. 1 página.
**CP:** Arthur executa o ciclo completo sozinho seguindo o README.
