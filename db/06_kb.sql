BEGIN;

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS kb_chunks (
    id          serial PRIMARY KEY,
    kind        text NOT NULL CHECK (kind IN ('schema','glossary','example')),
    title       text NOT NULL,
    content     text NOT NULL,
    embed_text  text NOT NULL,
    embedding   vector(384),
    tsv         tsvector GENERATED ALWAYS AS (to_tsvector('english', embed_text)) STORED
);

CREATE INDEX IF NOT EXISTS kb_chunks_embed_idx
    ON kb_chunks USING hnsw (embedding vector_cosine_ops);

CREATE INDEX IF NOT EXISTS kb_chunks_tsv_idx
    ON kb_chunks USING gin (tsv);

COMMIT;