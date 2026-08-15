-- Gansos Hub — schema v1.0
-- Executar via init_db.py; nunca editar manualmente o .db

CREATE TABLE IF NOT EXISTS profissionais (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    nome_sistema    TEXT    NOT NULL UNIQUE,
    funcao          TEXT    NOT NULL DEFAULT 'pendente',  -- barbeiro | manicure | assistente | recepcao_caixa | gerente | outro | pendente
    ativo           INTEGER NOT NULL DEFAULT 1            -- 1=ativo, 0=inativo
);

CREATE TABLE IF NOT EXISTS vendas (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    data_hora        TEXT    NOT NULL,    -- ISO 8601: YYYY-MM-DD HH:MM:SS
    valor            REAL    NOT NULL,
    tipo             TEXT    NOT NULL,    -- Serviço | Produto
    item             TEXT    NOT NULL,
    profissional_id  INTEGER REFERENCES profissionais(id),
    cliente          TEXT,
    comissao_sistema REAL,
    arquivo_origem   TEXT    NOT NULL,
    importado_em     TEXT    NOT NULL    -- ISO 8601 timestamp da ingestão
    -- dedup de reimportação: checar arquivo_origem em ingestao.py
);

CREATE TABLE IF NOT EXISTS categorias_produto (
    item_normalizado TEXT PRIMARY KEY,
    categoria        TEXT NOT NULL DEFAULT 'PENDENTE',  -- grooming | bar | PENDENTE
    origem           TEXT NOT NULL DEFAULT 'manual'     -- manual | regex
);

CREATE TABLE IF NOT EXISTS parametros (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    politica        TEXT    NOT NULL,  -- gratificacao_barbeiros | gratificacao_manicures | gratificacao_assistentes | gratificacao_recepcao_caixa
    chave           TEXT    NOT NULL,
    valor           TEXT    NOT NULL,  -- armazenado como texto; converter no código
    vigencia_inicio TEXT    NOT NULL,  -- YYYY-MM-DD
    vigencia_fim    TEXT,              -- NULL = em aberto
    profissional    TEXT,              -- NULL = aplica a todos da política; preenchido para metas individualizadas
    alterado_por    TEXT    NOT NULL DEFAULT 'sistema',
    alterado_em     TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS apuracoes (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    mes           TEXT    NOT NULL,  -- YYYY-MM
    politica      TEXT    NOT NULL,
    payload_json  TEXT    NOT NULL,  -- snapshot imutável (RN-21)
    publicada_em  TEXT    NOT NULL,
    UNIQUE (mes, politica)
);
