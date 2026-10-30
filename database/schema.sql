-- =============================================================
-- Mansão Amaldiçoada — esquema do banco (PostgreSQL)
-- Recria o banco do zero. Usado em produção (Render).
--   psql "$DATABASE_URL" -f database/schema.sql
-- O back-end também executa este arquivo sozinho ao iniciar,
-- então rodar manualmente é opcional.
-- =============================================================

-- Cada pessoa que entra na mansão vira um jogador (cadastro pelo nome).
CREATE TABLE IF NOT EXISTS jogadores (
    id         SERIAL PRIMARY KEY,
    nome       VARCHAR(30) NOT NULL UNIQUE,
    criado_em  BIGINT      NOT NULL            -- data em milissegundos (epoch)
);

-- Cada tentativa de fuga é uma partida (histórico completo).
CREATE TABLE IF NOT EXISTS partidas (
    id             SERIAL PRIMARY KEY,
    jogador_id     INTEGER     NOT NULL REFERENCES jogadores(id) ON DELETE CASCADE,
    token          VARCHAR(64) NOT NULL,                       -- "senha" da partida, só o navegador que criou conhece
    codigo_carta   VARCHAR(3)  NOT NULL,                       -- sorteada: combinação escrita na carta do baú
    fase           INTEGER     NOT NULL DEFAULT 1,             -- 1 a 4 (5 = escapou)
    status         VARCHAR(20) NOT NULL DEFAULT 'em_andamento', -- em_andamento | vitoria | derrota
    itens          TEXT        NOT NULL DEFAULT '',            -- inventário: "chave,carta"
    pistas         TEXT        NOT NULL DEFAULT '',            -- objetos já investigados: "1:livros,1:quadro"
    dicas          TEXT        NOT NULL DEFAULT '',            -- dicas pedidas: "1:sem_item,2:dicas"
    erros          INTEGER     NOT NULL DEFAULT 0,             -- senhas erradas
    pontos         INTEGER     NOT NULL DEFAULT 0,
    tempo_gasto    INTEGER,                                    -- segundos (preenchido ao terminar)
    iniciada_em    BIGINT      NOT NULL,
    finalizada_em  BIGINT
);

-- Conquistas desbloqueadas (cada jogador ganha cada uma só uma vez).
CREATE TABLE IF NOT EXISTS conquistas (
    id          SERIAL PRIMARY KEY,
    jogador_id  INTEGER     NOT NULL REFERENCES jogadores(id) ON DELETE CASCADE,
    partida_id  INTEGER     REFERENCES partidas(id) ON DELETE SET NULL,
    codigo      VARCHAR(30) NOT NULL,
    obtida_em   BIGINT      NOT NULL,
    UNIQUE (jogador_id, codigo)
);

-- Acelera a consulta do ranking (vitórias ordenadas por pontos e tempo).
CREATE INDEX IF NOT EXISTS idx_partidas_ranking ON partidas (status, pontos DESC, tempo_gasto);
CREATE INDEX IF NOT EXISTS idx_partidas_jogador ON partidas (jogador_id);
