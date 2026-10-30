-- =============================================================
-- Mansão Amaldiçoada — esquema do banco (SQLite)
-- Mesmas tabelas do schema.sql, na sintaxe do SQLite.
-- Usado quando o jogo roda localmente sem DATABASE_URL.
-- O back-end executa este arquivo sozinho ao iniciar.
-- =============================================================

CREATE TABLE IF NOT EXISTS jogadores (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    nome       TEXT    NOT NULL UNIQUE,
    criado_em  INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS partidas (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    jogador_id     INTEGER NOT NULL REFERENCES jogadores(id) ON DELETE CASCADE,
    token          TEXT    NOT NULL,
    codigo_carta   TEXT    NOT NULL,
    fase           INTEGER NOT NULL DEFAULT 1,
    status         TEXT    NOT NULL DEFAULT 'em_andamento',
    itens          TEXT    NOT NULL DEFAULT '',
    pistas         TEXT    NOT NULL DEFAULT '',
    dicas          TEXT    NOT NULL DEFAULT '',
    erros          INTEGER NOT NULL DEFAULT 0,
    pontos         INTEGER NOT NULL DEFAULT 0,
    tempo_gasto    INTEGER,
    iniciada_em    INTEGER NOT NULL,
    finalizada_em  INTEGER
);

CREATE TABLE IF NOT EXISTS conquistas (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    jogador_id  INTEGER NOT NULL REFERENCES jogadores(id) ON DELETE CASCADE,
    partida_id  INTEGER REFERENCES partidas(id) ON DELETE SET NULL,
    codigo      TEXT    NOT NULL,
    obtida_em   INTEGER NOT NULL,
    UNIQUE (jogador_id, codigo)
);

CREATE INDEX IF NOT EXISTS idx_partidas_ranking ON partidas (status, pontos DESC, tempo_gasto);
CREATE INDEX IF NOT EXISTS idx_partidas_jogador ON partidas (jogador_id);
