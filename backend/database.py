"""
Camada de acesso ao banco de dados.

- Em produção (Render) a variável DATABASE_URL aponta para um PostgreSQL.
- Localmente, sem DATABASE_URL, usamos um arquivo SQLite (database/mansao.db).

O resto do back-end só chama as funções deste arquivo, então não precisa
saber qual dos dois bancos está em uso.
"""

import os
import sqlite3
from pathlib import Path

PASTA_RAIZ = Path(__file__).resolve().parent.parent
PASTA_DATABASE = PASTA_RAIZ / 'database'

DATABASE_URL = os.environ.get('DATABASE_URL', '')
USA_POSTGRES = DATABASE_URL.startswith(('postgres://', 'postgresql://'))
CAMINHO_SQLITE = os.environ.get('SQLITE_PATH', str(PASTA_DATABASE / 'mansao.db'))


def conectar():
    if USA_POSTGRES:
        # Importado só aqui: quem roda local com SQLite não precisa do driver.
        import psycopg
        from psycopg.rows import dict_row
        return psycopg.connect(DATABASE_URL, row_factory=dict_row)

    conexao = sqlite3.connect(CAMINHO_SQLITE)
    conexao.row_factory = sqlite3.Row          # linhas acessíveis por nome da coluna
    conexao.execute('PRAGMA foreign_keys = ON')
    return conexao


def executar(sql, parametros=(), buscar=None):
    """
    Executa um comando SQL com parâmetros (nunca concatenamos texto do
    usuário no SQL, isso evita SQL Injection).

    buscar=None    -> não retorna nada (INSERT/UPDATE/DELETE)
    buscar='um'    -> retorna um dicionário ou None
    buscar='todos' -> retorna uma lista de dicionários
    """
    if USA_POSTGRES:
        sql = sql.replace('?', '%s')            # o psycopg usa %s em vez de ?

    conexao = conectar()
    try:
        cursor = conexao.cursor()
        cursor.execute(sql, parametros)

        resultado = None
        if buscar == 'um':
            linha = cursor.fetchone()
            resultado = dict(linha) if linha else None
        elif buscar == 'todos':
            resultado = [dict(linha) for linha in cursor.fetchall()]

        conexao.commit()
        return resultado
    finally:
        conexao.close()


def criar_banco():
    """Cria as tabelas (se ainda não existirem) a partir dos arquivos .sql."""
    arquivo = 'schema.sql' if USA_POSTGRES else 'schema_sqlite.sql'
    script = (PASTA_DATABASE / arquivo).read_text(encoding='utf-8')

    conexao = conectar()
    try:
        if USA_POSTGRES:
            conexao.execute(script)
        else:
            conexao.executescript(script)
        conexao.commit()
    finally:
        conexao.close()


def nome_do_banco():
    return 'postgresql' if USA_POSTGRES else 'sqlite'


# ---------------------------------------------------------------
# Jogadores
# ---------------------------------------------------------------

def buscar_ou_criar_jogador(nome, agora):
    jogador = executar(
        'SELECT id, nome FROM jogadores WHERE LOWER(nome) = LOWER(?)',
        (nome,), buscar='um')

    if jogador:
        return jogador

    return executar(
        'INSERT INTO jogadores (nome, criado_em) VALUES (?, ?) RETURNING id, nome',
        (nome, agora), buscar='um')


def buscar_jogador_por_nome(nome):
    return executar(
        'SELECT id, nome FROM jogadores WHERE LOWER(nome) = LOWER(?)',
        (nome,), buscar='um')


# ---------------------------------------------------------------
# Partidas
# ---------------------------------------------------------------

def criar_partida(jogador_id, token, agora, codigo_carta):
    return executar("""
        INSERT INTO partidas (jogador_id, token, codigo_carta, iniciada_em)
        VALUES (?, ?, ?, ?) RETURNING id
    """, (jogador_id, token, codigo_carta, agora), buscar='um')['id']


def buscar_partida(partida_id):
    return executar("""
        SELECT p.*, j.nome AS jogador
        FROM partidas p
        JOIN jogadores j ON j.id = p.jogador_id
        WHERE p.id = ?
    """, (partida_id,), buscar='um')


def atualizar_partida(partida):
    executar("""
        UPDATE partidas
        SET fase = ?, status = ?, itens = ?, pistas = ?, dicas = ?, erros = ?,
            pontos = ?, tempo_gasto = ?, iniciada_em = ?, finalizada_em = ?
        WHERE id = ?
    """, (partida['fase'], partida['status'], partida['itens'], partida['pistas'], partida['dicas'],
          partida['erros'], partida['pontos'], partida['tempo_gasto'], partida['iniciada_em'],
          partida['finalizada_em'], partida['id']))


def contar_vitorias(jogador_id):
    linha = executar(
        "SELECT COUNT(*) AS total FROM partidas WHERE jogador_id = ? AND status = 'vitoria'",
        (jogador_id,), buscar='um')
    return linha['total']


def historico_do_jogador(jogador_id, limite=8):
    return executar("""
        SELECT id, status, fase, pontos, erros, tempo_gasto, iniciada_em
        FROM partidas
        WHERE jogador_id = ? AND status <> 'em_andamento'
        ORDER BY iniciada_em DESC
        LIMIT ?
    """, (jogador_id, limite), buscar='todos')


# ---------------------------------------------------------------
# Ranking e estatísticas
# ---------------------------------------------------------------

def ranking(limite=10):
    # Cada jogador aparece uma vez, com a sua melhor fuga.
    return executar("""
        SELECT j.nome, p.pontos, p.tempo_gasto, p.erros, p.finalizada_em
        FROM partidas p
        JOIN jogadores j ON j.id = p.jogador_id
        WHERE p.status = 'vitoria'
          AND p.id = (
              SELECT p2.id FROM partidas p2
              WHERE p2.jogador_id = p.jogador_id AND p2.status = 'vitoria'
              ORDER BY p2.pontos DESC, p2.tempo_gasto ASC, p2.id ASC
              LIMIT 1
          )
        ORDER BY p.pontos DESC, p.tempo_gasto ASC
        LIMIT ?
    """, (limite,), buscar='todos')


def estatisticas():
    return executar("""
        SELECT
            (SELECT COUNT(*) FROM jogadores) AS jogadores,
            COUNT(*) AS partidas,
            COALESCE(SUM(CASE WHEN status = 'vitoria' THEN 1 ELSE 0 END), 0) AS vitorias,
            COALESCE(SUM(CASE WHEN status = 'derrota' THEN 1 ELSE 0 END), 0) AS derrotas
        FROM partidas
    """, buscar='um')


# ---------------------------------------------------------------
# Conquistas
# ---------------------------------------------------------------

def conquistas_do_jogador(jogador_id):
    linhas = executar(
        'SELECT codigo FROM conquistas WHERE jogador_id = ? ORDER BY obtida_em',
        (jogador_id,), buscar='todos')
    return [linha['codigo'] for linha in linhas]


def registrar_conquista(jogador_id, partida_id, codigo, agora):
    executar(
        'INSERT INTO conquistas (jogador_id, partida_id, codigo, obtida_em) VALUES (?, ?, ?, ?)',
        (jogador_id, partida_id, codigo, agora))


def limpar_tudo():
    executar('DELETE FROM conquistas')
    executar('DELETE FROM partidas')
    executar('DELETE FROM jogadores')
