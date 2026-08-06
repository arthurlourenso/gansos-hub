-- Gansos Hub — schema PostgreSQL v1.0
-- Executar via init_db.py com DATABASE_URL configurada

CREATE TABLE IF NOT EXISTS profissionais (
    id           SERIAL PRIMARY KEY,
    nome_sistema TEXT    NOT NULL UNIQUE,
    funcao       TEXT    NOT NULL DEFAULT 'pendente',
    ativo        INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS vendas (
    id               SERIAL PRIMARY KEY,
    data_hora        TIMESTAMP NOT NULL,
    valor            NUMERIC   NOT NULL,
    tipo             TEXT      NOT NULL,
    item             TEXT      NOT NULL,
    profissional_id  INTEGER   REFERENCES profissionais(id),
    cliente          TEXT,
    comissao_sistema NUMERIC,
    arquivo_origem   TEXT      NOT NULL,
    importado_em     TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS categorias_produto (
    item_normalizado TEXT PRIMARY KEY,
    categoria        TEXT NOT NULL DEFAULT 'PENDENTE',
    origem           TEXT NOT NULL DEFAULT 'manual'
);

CREATE TABLE IF NOT EXISTS parametros (
    id              SERIAL  PRIMARY KEY,
    politica        TEXT    NOT NULL,
    chave           TEXT    NOT NULL,
    valor           TEXT    NOT NULL,
    vigencia_inicio TEXT    NOT NULL,
    vigencia_fim    TEXT,
    alterado_por    TEXT    NOT NULL DEFAULT 'sistema',
    alterado_em     TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS apuracoes (
    id           SERIAL PRIMARY KEY,
    mes          TEXT   NOT NULL,
    politica     TEXT   NOT NULL,
    payload_json TEXT   NOT NULL,
    publicada_em TEXT   NOT NULL,
    UNIQUE (mes, politica)
);
