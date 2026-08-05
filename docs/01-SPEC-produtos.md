# SPEC — Comissionamento sobre Venda de Produtos
**Versão:** 1.0 · **Status:** aprovado

## 1. Problema
A venda de produtos fatura em média R$ 3.548/mês (jul/26: R$ 6.330, em aceleração), mas o
incentivo está invertido: barbeiros recebem 12% quando vendem produto; a gerente — responsável
por 61% de toda a venda — recebe ~2,4% (comissão irregular, configurada só em parte dos
produtos); a operadora de caixa vende com 0%. Quem mais vende é quem menos ganha.
Não existe metodologia formal: o que há é resíduo de configuração do sistema.

## 2. Objetivo
Criar um modelo de comissionamento formal, uniforme e autofinanciado para as vendas de
produtos registradas por gerência e caixa/atendimento, que estimule o crescimento da linha
de produtos sem comprometer a margem da casa.

## 3. Escopo
- INCLUI: vendas com Tipo="Produto" registradas por gerente, caixa e atendimento
  (hoje: Thamires, Sr. Nunes, Gerliane, Evelly — cadastro vivo, ver RN-06).
- NÃO INCLUI: comissão de barbeiros sobre produtos (12% atual, mantida como está);
  comissão sobre serviços; o programa de gratificação dos barbeiros (documento próprio).

## 4. Contexto de dados (jan–jul/2026)
- 787 vendas de produtos; média R$ 3.548/mês; tendência de alta (jul = 1,8x a média).
- Mix por receita: grooming (pomadas, leave-in, minoxidil) ≈ 55–60%; bar (Stella Gold,
  Heineken, whisky, energéticos, refrigerantes) ≈ 40–45%. Stella Gold é o item líder (R$ 6.658).
- Concentração: Thamires 61%; demais elegíveis somam ~13%; barbeiros ~26%.
- ATENÇÃO (RN-05): o campo "Profissional" registra quem LANÇOU a venda, não necessariamente
  quem vendeu — auxiliares vendem bar e repassam o lançamento à gerência/caixa.

## 5. Regras de negócio
- **RN-01 (Base de cálculo):** comissão incide sobre o VALOR DA VENDA do produto, apurada
  mensalmente por profissional elegível, paga junto ao fechamento do mês seguinte.
- **RN-02 (Percentuais por categoria):** produtos de grooming: **8%**; itens de bar/consumo:
  **4%**. Racional: grooming tem margem maior e depende de venda consultiva; bar tem venda
  passiva e margem menor. [DEFAULT — sujeito à Decisão D1]
- **RN-03 (Meta de aceleração):** se a receita TOTAL de produtos do mês ≥ **R$ 5.000**,
  bônus adicional de **R$ 150** dividido igualmente entre os elegíveis do mês. Meta revisada
  trimestralmente. [DEFAULT — sujeito à Decisão D2]
- **RN-04 (Guardrail financeiro):** custo total do comissionamento ≤ **25% da margem bruta**
  dos produtos no mês. Se o CMV apurado indicar violação, os percentuais RN-02 são reduzidos
  proporcionalmente no trimestre seguinte. Depende da Decisão D3 (CMV).
- **RN-05 (Titularidade da venda):** a comissão pertence a quem consta no campo Profissional
  do lançamento. Consequência: quem lança leva — a regra é simples, mas exige disciplina de
  lançamento correto. Comunicar explicitamente à equipe.
- **RN-06 (Elegibilidade):** lista nominal de elegíveis mantida pela gestão (funções: gerente,
  caixa, atendimento). Barbeiros ficam fora deste modelo (mantêm os 12% atuais).
- **RN-07 (Uniformidade no sistema):** a configuração de comissão por produto no AppBarber
  deve ser padronizada conforme RN-02 — eliminando o estado atual em que produtos iguais
  comissionam diferente dependendo do cadastro.

## 6. Critérios de aceite (da metodologia implantada)
- CA-1: dado um mês de vendas, a apuração produz por elegível: receita por categoria,
  comissão calculada, bônus de meta (se houver) e total a pagar — reproduzível e auditável.
- CA-2: aplicada retroativamente a jan–jul/2026, a apuração fecha sem erro e o custo mensal
  do modelo fica entre R$ 150 e R$ 600 no nível atual de vendas.
- CA-3: nenhum elegível recebe menos no novo modelo do que recebia no estado atual
  (a Thamires não pode perder os ~R$ 52/mês médios que já recebe).
- CA-4: o guardrail RN-04 é verificável no relatório mensal.

## 7. Estimativa de custo (defaults, nível atual de vendas)
Receita média R$ 3.548/mês → comissão estimada ≈ R$ 220/mês (blend 8%/4% no mix atual)
+ bônus de meta em meses ≥ R$ 5k. No cenário de julho (R$ 6.330): ≈ R$ 390 + R$ 150 de
bônus. Custo anual estimado: R$ 3–5 mil, contra uma linha de receita de R$ 42–75 mil/ano
em crescimento. Autofinanciamento análogo ao programa dos barbeiros.

## 8. PENDÊNCIAS DE DECISÃO (donas: gestão — bloqueiam a execução)
- **D1:** valida os percentuais 8% (grooming) / 4% (bar)? Alternativa: % único simples (6%). decisão: percentuais diferentes para os itens e mantemos a primeira opção.
- **D2:** valida meta de R$ 5.000 e bônus de R$ 150? Decisão: ok
- **D3:** existe CMV por produto disponível (sistema de estoque)? Sem ele, o guardrail RN-04
  opera com margem ASSUMIDA de 50% — registrar como premissa. Decisão: assuma 50% de margem.
- **D4:** a comissão dos barbeiros sobre produtos permanece 12% (fora do escopo) ou será
  unificada com este modelo no futuro? decisão: permanece por enquanto.
