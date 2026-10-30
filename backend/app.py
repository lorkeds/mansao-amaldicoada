"""
Servidor da Mansão Amaldiçoada (Flask).

Faz duas coisas:
1. Entrega o front-end (pasta frontend/) para o navegador.
2. Oferece a API /api/... que o jogo usa para criar partidas, investigar
   objetos, conferir senhas, salvar pontuação e mostrar o ranking.

Executar localmente:  python backend/app.py
Em produção (Render): gunicorn --chdir backend app:app
"""

import os
import re
import secrets
import time
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

import database
import jogo

PASTA_FRONTEND = Path(__file__).resolve().parent.parent / 'frontend'

# static_url_path='' faz /css/style.css, /js/game.js e /assets/... saírem direto da pasta frontend/
app = Flask(__name__, static_folder=str(PASTA_FRONTEND), static_url_path='')
app.json.ensure_ascii = False        # acentos aparecem normais no JSON

database.criar_banco()

NOME_VALIDO = re.compile(r"^[\wÀ-ÿ .'-]{2,30}$")


def agora_ms():
    return int(time.time() * 1000)


def erro(mensagem, status=400):
    return jsonify({'erro': mensagem}), status


def carregar_partida(partida_id):
    """
    Busca a partida e confere o token enviado pelo navegador no cabeçalho
    X-Partida-Token. Sem o token certo ninguém mexe na partida dos outros.
    Retorna (partida, None) ou (None, resposta_de_erro).
    """
    partida = database.buscar_partida(partida_id)
    if partida is None:
        return None, erro('Partida não encontrada.', 404)

    token = request.headers.get('X-Partida-Token', '')
    if not secrets.compare_digest(token, partida['token']):
        return None, erro('Token da partida inválido.', 403)

    return partida, None


def montar_estado(partida, mensagem=None, efeito=None, conquistas_novas=None):
    estado = jogo.estado_publico(partida, agora_ms())
    estado['mensagem'] = mensagem
    estado['efeito'] = efeito
    estado['conquistas_novas'] = [
        {'codigo': codigo, **jogo.CONQUISTAS[codigo]} for codigo in (conquistas_novas or [])
    ]
    return estado


def responder_com_estado(partida, mensagem=None, efeito=None, conquistas_novas=None):
    return jsonify(montar_estado(partida, mensagem, efeito, conquistas_novas))


def finalizar_se_venceu(partida, efeito):
    """Ao vencer, registra as conquistas novas no banco e as devolve."""
    if efeito != 'vitoria':
        return []

    anteriores = database.contar_vitorias(partida['jogador_id'])
    ja_tem = set(database.conquistas_do_jogador(partida['jogador_id']))
    novas = [c for c in jogo.conquistas_merecidas(partida, anteriores) if c not in ja_tem]

    for codigo in novas:
        database.registrar_conquista(partida['jogador_id'], partida['id'], codigo, agora_ms())
    return novas


# ---------------------------------------------------------------
# Front-end
# ---------------------------------------------------------------

@app.get('/')
def inicio():
    return send_from_directory(PASTA_FRONTEND, 'index.html')


# ---------------------------------------------------------------
# API
# ---------------------------------------------------------------

@app.get('/api/saude')
def saude():
    """Usado para conferir se o servidor e o banco estão no ar."""
    database.estatisticas()
    return jsonify({'status': 'ok', 'banco': database.nome_do_banco()})


@app.post('/api/partidas')
def nova_partida():
    dados = request.get_json(silent=True) or {}
    nome = ' '.join(str(dados.get('nome', '')).split())   # tira espaços repetidos

    if not NOME_VALIDO.match(nome):
        return erro('Digite um nome de 2 a 30 letras (sem símbolos especiais).')

    agora = agora_ms()
    jogador = database.buscar_ou_criar_jogador(nome, agora)
    token = secrets.token_hex(16)
    # Cada partida tem a sua combinação do cadeado final: quem decorou a de outra partida não se dá bem
    partida_id = database.criar_partida(jogador['id'], token, agora, jogo.sortear_codigo_carta())

    partida = database.buscar_partida(partida_id)
    estado = montar_estado(
        partida, f'🕯️ {jogador["nome"]}, as portas se fecham atrás de você... Encontre a saída!')
    estado['token'] = token  # o token só é enviado uma vez, na criação
    return jsonify(estado), 201


@app.get('/api/partidas/<int:partida_id>')
def ver_partida(partida_id):
    partida, falha = carregar_partida(partida_id)
    if falha:
        return falha

    if jogo.verificar_tempo(partida, agora_ms()):
        database.atualizar_partida(partida)
        return responder_com_estado(partida, '💀 O tempo acabou! A mansão venceu desta vez.', 'derrota')

    return responder_com_estado(partida)


@app.post('/api/partidas/<int:partida_id>/investigar')
def investigar(partida_id):
    partida, falha = carregar_partida(partida_id)
    if falha:
        return falha

    if jogo.verificar_tempo(partida, agora_ms()):
        database.atualizar_partida(partida)
        return responder_com_estado(partida, '💀 O tempo acabou! A mansão venceu desta vez.', 'derrota')

    if partida['status'] != 'em_andamento':
        return erro('Esta partida já terminou.', 409)

    dados = request.get_json(silent=True) or {}
    mensagem, efeito = jogo.investigar(partida, str(dados.get('objeto', '')))
    database.atualizar_partida(partida)
    return responder_com_estado(partida, mensagem, efeito)


@app.post('/api/partidas/<int:partida_id>/responder')
def responder(partida_id):
    partida, falha = carregar_partida(partida_id)
    if falha:
        return falha

    agora = agora_ms()
    if jogo.verificar_tempo(partida, agora):
        database.atualizar_partida(partida)
        return responder_com_estado(partida, '💀 O tempo acabou! A mansão venceu desta vez.', 'derrota')

    if partida['status'] != 'em_andamento':
        return erro('Esta partida já terminou.', 409)

    dados = request.get_json(silent=True) or {}
    resposta = str(dados.get('resposta', '')).strip()
    if not resposta.isdigit() or len(resposta) > 6:
        return erro('Digite apenas números.')

    mensagem, efeito = jogo.responder(partida, resposta, agora)
    novas = finalizar_se_venceu(partida, efeito)
    database.atualizar_partida(partida)
    return responder_com_estado(partida, mensagem, efeito, novas)


@app.post('/api/partidas/<int:partida_id>/dica')
def dica(partida_id):
    partida, falha = carregar_partida(partida_id)
    if falha:
        return falha

    agora = agora_ms()
    if jogo.verificar_tempo(partida, agora):
        database.atualizar_partida(partida)
        return responder_com_estado(partida, '💀 O tempo acabou! A mansão venceu desta vez.', 'derrota')

    if partida['status'] != 'em_andamento':
        return erro('Esta partida já terminou.', 409)

    mensagem, efeito = jogo.pedir_dica(partida, agora)
    database.atualizar_partida(partida)
    return responder_com_estado(partida, mensagem, efeito)


@app.post('/api/partidas/<int:partida_id>/desistir')
def desistir(partida_id):
    partida, falha = carregar_partida(partida_id)
    if falha:
        return falha

    if partida['status'] == 'em_andamento':
        agora = agora_ms()
        partida['status'] = 'derrota'
        partida['tempo_gasto'] = min(jogo.TEMPO_LIMITE, jogo.segundos_passados(partida, agora))
        partida['pontos'] = 0
        partida['finalizada_em'] = agora
        database.atualizar_partida(partida)

    return responder_com_estado(partida, '🏳️ Você desistiu... a mansão guarda mais uma alma.', 'derrota')


@app.get('/api/ranking')
def ranking():
    return jsonify(database.ranking())


@app.get('/api/estatisticas')
def estatisticas():
    dados = database.estatisticas()
    return jsonify({chave: int(valor or 0) for chave, valor in dados.items()})


@app.get('/api/jogadores/<nome>')
def perfil_jogador(nome):
    jogador = database.buscar_jogador_por_nome(nome.strip())
    if jogador is None:
        return erro('Jogador não encontrado.', 404)

    codigos = database.conquistas_do_jogador(jogador['id'])
    return jsonify({
        'nome': jogador['nome'],
        'historico': database.historico_do_jogador(jogador['id']),
        'conquistas': [{'codigo': c, **jogo.CONQUISTAS[c]} for c in codigos],
        'todas_conquistas': len(jogo.CONQUISTAS),
    })


# Erros da API sempre em JSON (o front-end sabe ler).
@app.errorhandler(404)
def nao_encontrado(_):
    if request.path.startswith('/api/'):
        return erro('Rota não encontrada.', 404)
    return send_from_directory(PASTA_FRONTEND, 'index.html'), 404


@app.errorhandler(500)
def erro_interno(_):
    return erro('Erro interno no servidor. Tente de novo.', 500)


if __name__ == '__main__':
    porta = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=porta, debug=os.environ.get('FLASK_DEBUG') == '1')
