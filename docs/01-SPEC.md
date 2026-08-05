# SPEC — Gansos Hub
**Versão:** 1.1 · **Status:** F1/F2/F4 liberadas; F3 aguarda D1 (spec de produtos)

## 1. Problema
As informações vivem espalhadas: vendas de serviços num tipo de export, produtos em arquivos
mensais avulsos, análises refeitas manualmente a cada rodada, e três políticas de incentivo
(barbeiros, recepção/caixa, e as pendentes de manicures/assistentes) documentadas em
propostas separadas, sem apuração centralizada. Não existe fonte única da verdade.

## 2. Objetivo
Centralizar ingestão, análise e apuração numa plataforma local: base unificada + dashboard
+ motor de apuração de incentivos com parâmetros versionados — reduzindo a apuração mensal
a: importar exports → conferir → publicar.

## 3. Fases e escopo
- **F1 — Fundação (este pacote executa):** base unificada, ingestão dos dois layouts de
  export, relatório de vendas (serviços + produtos) e harness.
- **F2 — Barbeiros (este pacote executa):** ticket médio e itens/atendimento por barbeiro,
  apuração da gratificação (regras RN-10).
- **F3 — Produtos (este pacote executa):** apuração da comissão de recepção/caixa conforme
  a spec do pacote sdd-comissionamento (RN-01 a RN-07 de lá valem aqui por referência).
- **F4 — Manicures e assistentes (este pacote executa):** gratificação por faturamento
  mensal conforme RN-12 e RN-13. Políticas aprovadas em 05/08/2026.

## 4. Regras de negócio
- **RN-10 (Gratificação barbeiros):** métrica = ticket médio mensal (serviços; atendimento =
  cliente+dia+profissional). Níveis: Bronze ≥ R$ 120 → R$ 150; Prata ≥ R$ 135 → R$ 300;
  Ouro ≥ R$ 150 → R$ 500. Elegibilidade: ≥ 50 atendimentos/mês. Parâmetros com vigência
  trimestral — a apuração de um mês usa a regra vigente NAQUELE mês.
- **RN-11 (Comissão produtos):** por referência, a spec sdd-comissionamento v1.0 na íntegra
  (grooming 8% / bar 4%, meta coletiva R$ 5.000 → bônus R$ 150, guardrail 25% da margem).
- **RN-12 (Gratificação manicures):** métrica = faturamento mensal registrado (serviços).
  Níveis: Bronze ≥ R$ 6.000 → R$ 150; Prata ≥ R$ 8.000 → R$ 300; Ouro ≥ R$ 10.000 → R$ 500.
  Sem mínimo de atendimentos (meta em valor absoluto dispensa guardrail de volume).
  Paga por cima da comissão vigente (42,9% média). Revisão trimestral.
- **RN-13 (Gratificação assistentes):** métrica = faturamento mensal registrado (SOMENTE
  serviços executados; vendas de bar seguem lançadas pela recepção/caixa e ficam fora).
  Níveis: Bronze ≥ R$ 2.500 → R$ 100; Prata ≥ R$ 3.500 → R$ 200; Ouro ≥ R$ 5.000 → R$ 350.
  Sem mínimo de atendimentos. Paga por cima da comissão vigente (23,6% média). Revisão
  trimestral. Raynara de Cassia: desligada em jul/2026 — histórico preservado, fora de
  apurações a partir de ago/2026.
- **RN-20 (Parâmetros editáveis):** todo número de política (metas, %, prêmios, mínimos)
  vive em tabelas com vigência. Editar parâmetro NUNCA exige mexer em código. Alterações
  ficam registradas (quem/quando) para auditoria.
- **RN-21 (Imutabilidade da apuração):** apuração publicada de um mês não muda quando
  parâmetros futuros mudam.
- **RN-30 (Extensibilidade):** profissionais têm função (barbeiro, manicure, assistente,
  recepcao_caixa, gerente, outro). O modelo de dados comporta novas políticas por função
  sem migração estrutural.
- **RN-31 (Dado bruto preservado):** todo import guarda o arquivo de origem e linhas
  rejeitadas são reportadas, nunca descartadas em silêncio.

## 5. Critérios de aceite do projeto
- CA-1: importar um export novo (qualquer dos dois layouts) exige um comando e termina com
  resumo do que entrou/rejeitou/duplicou.
- CA-2: o dashboard responde num mesmo lugar: vendas do mês (serviços+produtos), ticket
  médio por barbeiro contra as metas, e apuração de gratificações/comissões do mês.
- CA-3: o retroativo jan–jul/2026 reproduz os números de referência do harness (04-HARNESS.md).
- CA-4: alterar uma meta pelo painel de parâmetros reflete na apuração do mês seguinte sem
  tocar em código (RN-20/RN-21 demonstradas).

## 6. Fora de escopo (nesta versão)
Automação de envio (WhatsApp/e-mail), acesso multiusuário/web público, integração direta
com API do AppBarber (segue via export manual), CRM.

## 7. PENDÊNCIAS DE DECISÃO
- **D1:** as decisões D1–D4 da spec de produtos (percentuais, meta, CMV, barbeiros 12%)
  seguem pendentes — bloqueiam a F3, não a F1/F2.
- **D2:** RESOLVIDA (05/08/2026) — métrica de faturamento mensal, réguas em RN-12/RN-13.
- **D3:** onde o Hub roda no dia a dia — máquina do Arthur (default) ou máquina da gerência?
