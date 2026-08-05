# PLAN — Gansos Hub
**Deriva de:** 01-SPEC v1.0. Stack: Python 3.11+ · SQLite · Streamlit · pytest.

## 1. Estrutura do repositório
```
gansos-hub/
├── docs/            # este pacote SDD + spec de produtos referenciada
├── dados/entrada/   # exports .xlsx a importar (não versionados no git)
├── db/gansos.db     # SQLite (não versionado)
├── src/             # ingestao.py, apuracao_barbeiros.py, apuracao_produtos.py, dashboard.py
├── harness/         # verificar.py + testes pytest + golden_numbers.json
└── README.md
```

## 2. Modelo de dados (SQLite)
- `profissionais(id, nome_sistema, funcao, ativo)` — funcao conforme RN-30; novos nomes
  entram como 'pendente' e a apuração ignora pendentes com aviso.
- `vendas(id, data_hora, valor, tipo, item, profissional_id, cliente, comissao_sistema,
  arquivo_origem, importado_em)` — serviços E produtos na mesma tabela; dedup por chave
  natural (data_hora+profissional+cliente+item+valor).
- `categorias_produto(item_normalizado, categoria, origem)` — grooming|bar|PENDENTE.
- `parametros(id, politica, chave, valor, vigencia_inicio, vigencia_fim, alterado_por,
  alterado_em)` — politica ∈ {gratificacao_barbeiros, comissao_produtos, ...}. RN-20/21.
- `apuracoes(id, mes, politica, payload_json, publicada_em)` — snapshot imutável (RN-21).

## 3. Ingestão
Dois layouts, mesma normalização final: (a) export geral de serviços (com ou sem aba
Funcionario); (b) exports mensais de produtos. Correção obrigatória do styles.xml corrompido
(reempacotar zip com stylesheet mínimo). Normalizar moeda BR e datas dd/mm/aaaa hh:mm:ss.
Relatório de import: linhas lidas / inseridas / duplicadas / rejeitadas (RN-31).

## 4. Apuração
Funções puras `apurar_barbeiros(mes)` e `apurar_produtos(mes)` que leem vendas + parâmetros
vigentes no mês e retornam DataFrames; publicação grava snapshot em `apuracoes`.
Atendimento (barbeiros) = groupby(cliente, date(data_hora), profissional) sobre tipo=Serviço.

## 5. Dashboard (Streamlit, abas)
1. **Vendas** — receita do mês por tipo/categoria/profissional, comparativo mensal.
2. **Barbeiros** — ticket médio × metas (linhas Bronze/Prata/Ouro), itens/atendimento,
   elegibilidade, evolução histórica.
3. **Apuração** — quadro do mês: gratificações + comissões, custo total, botão publicar.
4. **Parâmetros** — edição com vigência (grava em `parametros`, nunca no código).

## 6. Riscos
Grafia livre de itens e nomes → normalização + fila de pendentes; mudança de layout do
export → validação de colunas com erro explícito; sobreposição de períodos entre arquivos
→ dedup da §2 resolve por construção.
