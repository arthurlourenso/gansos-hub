# HARNESS — Números de referência (golden numbers)
Verificações automatizadas. Fonte: análises validadas de jan–jul/2026. Tolerância zero
salvo indicação. O executor NUNCA edita este arquivo para "fazer passar".

## H1 — Volume (após T2)
- Produtos consolidados (7 arquivos mensais): **787 linhas**, soma **R$ 24.833,00**.
- Produtos por mês (soma R$): jan 2.174 · fev 3.547 · mar 3.284 · abr 2.968 · mai 3.933 ·
  jun 2.597 · jul 6.330.
- Zero valores monetários nulos após normalização; zero linhas com data inválida.

## H2 — Ticket médio barbeiros (após T4; base jun+jul/2026; tolerância ±R$ 0,05)
- Mateus Lima: **R$ 153,77** · William Silva Melo: **R$ 121,14** · Davi Silva Martins:
  **R$ 112,03→112,14** (usar 112,14) · Caique Campos Ferreira: **R$ 102,68** ·
  Getúlio S. N. Junior: **R$ 127,65**.
- Atendimentos jun+jul: William **426** · Davi **292** · Caique **207**.
- Thiago Siqueira: 46 atendimentos em 2 meses → em qualquer mês isolado deve constar
  como INELEGÍVEL (abaixo do mínimo 50).

## H3 — Produtos/comissão (após T5)
- Thamires Ferreira: receita 7m **R$ 15.167** (651 vendas) — maior vendedora.
- Sr. Nunes (Leandro J. F. Nunes): receita 7m **R$ 721**, comissão de sistema **R$ 0,00**.
- Categorização: itens contendo STELLA, HEINEKEN, WHISKY, RED BULL, COCA → bar;
  POMADA, LEAVE-IN, MINOXIDIL, SHAMPOO → grooming; cobertura ≥ 95% da receita sem PENDENTE.
- Simulação com defaults (8%/4%): custo mensal do modelo entre **R$ 150 e R$ 600** em
  todos os meses de jan–jul (CA-2 da spec de produtos).

## H5 — Faturamento mensal manicures/assistentes (após T5b; base jan–jun/2026; tolerância ±R$ 5)
- Manicures (média/mês): Hilda **10.458** · Esmeralda **9.164** · Isaura **7.957** ·
  Rayssa **6.479** · Safira **4.858**. Comissão média da função: **42,9%**.
- Assistentes (média/mês): Maria Aparecida **3.316** · Suzan **2.924** · Ana Mayra **518** ·
  Raynara **57**. Comissão média da função: **23,6%**.
- Aplicando RN-12 à média jan–jun: Hilda=Ouro, Esmeralda=Prata, Isaura=Bronze,
  Rayssa=Bronze, Safira=sem nível. Custo: R$ 1.100/mês.
- Aplicando RN-13: Maria=Bronze, Suzan=Bronze, Ana=sem nível. Custo: R$ 200/mês.

## H4 — Integridade (contínuo)
- Reimportar um arquivo já importado: **0 inserções novas** (dedup).
- Nenhum profissional 'pendente' com vendas entra em apuração sem aviso explícito.
- Apuração publicada: re-rodar com parâmetros novos NÃO altera o snapshot (RN-21).
