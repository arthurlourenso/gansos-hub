# Guia de Execução — Gansos Hub (SDD + Harness)
**Projeto:** Plataforma unificada de dados e incentivos — Gansos Barbearia
**Metodologia:** Spec-Driven Development + Harness de verificação automatizada
**Planejamento:** Arthur (Financeiro) · **Execução:** modelos leves via Claude Code

## O que este projeto é
Uma base local única (SQLite) que ingere os exports do AppBarber (serviços + produtos),
alimenta um dashboard (Streamlit) com relatório de vendas, ticket médio dos barbeiros e
apuração mensal de gratificações/comissões — com parâmetros editáveis conforme as metas
evoluem. Este projeto ABSORVE os planejamentos anteriores: o "Gansos Dashboard" (barbeiros)
e o comissionamento de produtos (pacote sdd-comissionamento) viram fases daqui.

## Papéis dos documentos
| Documento | Papel |
|---|---|
| 01-SPEC.md | Regras de negócio e critérios de aceite — fonte da verdade |
| 02-PLAN.md | Arquitetura, modelo de dados, decisões técnicas |
| 03-TASKS.md | Unidades executáveis, uma por vez, com critério de pronto |
| 04-HARNESS.md | Verificações automatizadas que validam cada task |

## Regras para o executor
1. Regra de negócio vem SOMENTE da SPEC (e da spec de produtos referenciada). Ambiguidade = parar e perguntar.
2. Após CADA task: rodar `python harness/verificar.py` e colar a saída. Task sem harness verde não está pronta.
3. Commit por task concluída. Nunca reescrever histórico.
4. Entregar o mínimo que passa — sem otimização não pedida.

## Ordem
T1 → T2 → T3 (fundação). Depois T4 e T5 em qualquer ordem. T6 depende de T4+T5. T7 e T8 por último.
