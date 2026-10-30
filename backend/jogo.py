"""
Regras do jogo Mansão Amaldiçoada.

Todo o "cérebro" do escape room fica aqui, no servidor:
- quais objetos existem em cada fase e o que cada um revela;
- o SORTEIO da combinação do cadeado final (muda a cada jogo);
- as senhas (o navegador nunca recebe as respostas);
- as dicas, que custam tempo;
- o cronômetro oficial (calculado pela hora de início gravada no banco);
- a pontuação e as conquistas.

Assim ninguém consegue trapacear editando o JavaScript no navegador.
"""

import random

TEMPO_LIMITE = 300          # 5 minutos, em segundos
PONTOS_POR_SEGUNDO = 10     # cada segundo que sobra vale 10 pontos
PENALIDADE_POR_ERRO = 50    # cada senha errada tira 50 pontos
CUSTO_DICA = 20             # cada dica tira 20 segundos do relógio
FASE_FINAL = 4

# A senha do quarto é sempre a mesma: o dia 13 de outubro está desenhado no
# calendário da imagem. Quem muda a cada partida é a combinação da carta do baú.
SENHA_QUARTO = '1310'

# Os textos podem ter {codigo_carta} e {codigo_carta_separado}: são trocados
# pela combinação sorteada para a partida (função variaveis()).
# Cada fase tem objetos clicáveis. Um objeto pode:
#   - só mostrar um texto (pista);
#   - 'da_item': colocar um item no inventário;
#   - 'precisa_item' + 'avanca': levar para a próxima fase se o jogador tiver o item;
#   - 'foca_senha': indicar ao front-end que deve focar o campo de senha;
#   - 'efeito': 'susto': o front-end treme a tela e toca um som assustador.
# Os objetos marcados com "ambiente" não são necessários para escapar: dão
# clima, algumas pistas extras e um ou outro susto (e contam para a conquista Detetive).
FASES = {
    1: {
        'nome': 'Biblioteca Esquecida',
        'objetivo': 'Investigue a biblioteca e descubra como abrir a porta.',
        'objetos': {
            'livros': {
                'rotulo': 'Investigar a estante',
                'emoji': '📚',
                'texto': 'Entre livros empoeirados, uma anotação: "O segredo está atrás do retrato."',
            },
            'quadro': {
                'rotulo': 'Investigar o retrato',
                'emoji': '🖼️',
                'texto': '🔑 Atrás do retrato havia uma chave enferrujada! Ela foi para o seu inventário.',
                'da_item': 'chave',
            },
            'porta': {
                'rotulo': 'Abrir a porta',
                'emoji': '🚪',
                'texto_bloqueado': '🔒 A porta está trancada com correntes. Procure uma chave.',
                'texto': '🚪 A chave serviu! A porta range e você entra no quarto...',
                'precisa_item': 'chave',
                'avanca': True,
            },
            # ambiente
            'janela': {
                'rotulo': 'Olhar pela janela', 'emoji': '🌕',
                'texto': '🌕 A lua cheia ilumina o jardim. Por um instante, uma silhueta pálida acena lá fora... e some.',
                'efeito': 'susto',
            },
            'globo': {
                'rotulo': 'Girar o globo', 'emoji': '🌍',
                'texto': '🌍 O globo gira sozinho e para sempre no mesmo lugar: um ponto marcado "Mansão — não volte".',
            },
            'poltrona': {
                'rotulo': 'Examinar a poltrona', 'emoji': '🪑',
                'texto': '🪑 A poltrona ainda está morna, como se alguém tivesse acabado de levantar.',
            },
            'mesa': {
                'rotulo': 'Ler o livro aberto na mesa', 'emoji': '📖',
                'texto': '📖 Um diário aberto: "Escondi a chave onde a dona da casa sempre nos observa."',
            },
            'caveira': {
                'rotulo': 'Examinar a caveira', 'emoji': '💀',
                'texto': '💀 Uma caveira sobre a lareira. Alguém escreveu na testa dela: "Não toque em nada."',
            },
            'busto': {
                'rotulo': 'Examinar o busto', 'emoji': '🗿',
                'texto': '🗿 Um busto de mármore. A placa diz: "Barão Valdemar, que nunca saiu desta casa".',
            },
            'gargula': {
                'rotulo': 'Olhar a gárgula', 'emoji': '🦇',
                'texto': '🦇 A gárgula de pedra sobre a porta parece ter virado a cabeça na sua direção...',
                'efeito': 'susto',
            },
            'lustre': {
                'rotulo': 'Olhar o lustre', 'emoji': '🕯️',
                'texto': '🕯️ As velas do lustre tremem, mas não há vento nenhum aqui dentro.',
            },
        },
    },
    2: {
        'nome': 'Quarto Amaldiçoado',
        'objetivo': 'Investigue o quarto e descubra a senha de 4 dígitos da passagem secreta.',
        'objetos': {
            'calendario': {
                'rotulo': 'Investigar o calendário',
                'emoji': '📅',
                'texto': '📅 O dia 13 de outubro está circulado em vermelho. 13 e 10 parecem importantes...',
            },
            'relogio': {
                'rotulo': 'Investigar o relógio',
                'emoji': '🕰️',
                'texto': '🕰️ O relógio está parado. Uma inscrição diz: "Primeiro o dia, depois o mês."',
            },
            'porta': {
                'rotulo': 'Examinar o cadeado da porta',
                'emoji': '🔐',
                'texto': '🔐 Um cadeado de 4 dígitos. Um bilhete diz: "O dia do azar e o mês das bruxas '
                         'guardam a combinação."',
                'foca_senha': True,
            },
            # ambiente
            'retrato': {
                'rotulo': 'Olhar o retrato oval', 'emoji': '🖼️',
                'texto': '🖼️ Um homem de olhar vazio. No canto da moldura, riscado: "Sexta-feira 13 foi o último dia dele aqui".',
            },
            'cama': {
                'rotulo': 'Examinar a cama', 'emoji': '🛏️',
                'texto': '🛏️ Os lençóis estão amarrotados e gelados. Debaixo do travesseiro, só pó e uma pena de corvo.',
            },
            'bau': {
                'rotulo': 'Abrir o baú do quarto', 'emoji': '🧳',
                'texto': '🧳 O baú está cheio de roupas antigas com cheiro de mofo. Nada útil... por enquanto.',
            },
            'janela': {
                'rotulo': 'Olhar pela janela', 'emoji': '🌕',
                'texto': '😱 Um rosto pálido encosta no vidro do lado de fora! Você pisca... e não há mais ninguém.',
                'efeito': 'susto',
            },
            'portarretrato': {
                'rotulo': 'Pegar o porta-retrato', 'emoji': '🪞',
                'texto': '🪞 Uma foto antiga da família. Todos sorriem, menos a criança do canto, que olha direto para você.',
            },
            'caveira': {
                'rotulo': 'Examinar a caveira com a vela', 'emoji': '💀',
                'texto': '💀 A vela ao lado da caveira nunca derrete. Ela ilumina um livro de feitiços fechado a sete chaves.',
            },
        },
        'senha': {'tamanho': 4, 'rotulo': 'Senha da passagem (4 dígitos)',
                  'dica_erro': '❌ Senha incorreta! Dica: pense em uma data assustadora.',
                  'texto_acerto': '🔓 A passagem secreta se abriu! Você desce para o Porão Assombrado.'},
    },
    3: {
        'nome': 'Porão Assombrado',
        'objetivo': 'Encontre o que está escondido no porão e descubra como subir a escadaria.',
        'objetos': {
            'bau': {
                'rotulo': 'Abrir o baú',
                'emoji': '🧰',
                'texto': '📜 Dentro do baú, uma carta antiga: "Para deixar esta mansão, siga além da escadaria. '
                         'O cadeado obedece a três números: {codigo_carta_separado}."',
                'da_item': 'carta',
            },
            'retrato': {
                'rotulo': 'Olhar o retrato na parede',
                'emoji': '👻',
                'texto': '👻 Os olhos do retrato parecem seguir você... e apontam para o baú perto da lamparina.',
            },
            'escadaria': {
                'rotulo': 'Subir a escadaria',
                'emoji': '🪜',
                'texto_bloqueado': '🌫️ Uma névoa gelada empurra você de volta. Talvez algo no porão ajude.',
                'texto': '🪜 Você sobe a escadaria e encontra uma porta pesada com um cadeado...',
                'precisa_item': 'carta',
                'avanca': True,
            },
            # ambiente
            'cranio': {
                'rotulo': 'Examinar o crânio na prateleira', 'emoji': '💀',
                'texto': '💀 Um crânio coberto de teias. Embaixo dele, um bilhete: "Cartas antigas guardam segredos".',
            },
            'castical': {
                'rotulo': 'Examinar o castiçal', 'emoji': '🕯️',
                'texto': '🕯️ As velas do castiçal se acendem sozinhas quando você chega perto.',
            },
            'lamparina': {
                'rotulo': 'Examinar a lamparina', 'emoji': '🏮',
                'texto': '🏮 A lamparina ilumina o baú logo abaixo dela. A tampa parece ter sido aberta há pouco tempo.',
            },
            'barril': {
                'rotulo': 'Bater no barril', 'emoji': '🛢️',
                'texto': '😱 TOC, TOC... Alguma coisa bate de volta, de DENTRO do barril!',
                'efeito': 'susto',
            },
            'mesa': {
                'rotulo': 'Examinar a mesa', 'emoji': '🧪',
                'texto': '🧪 Frascos com líquidos estranhos e um caderno de anotações rasgado: "...nunca suba sem a carta..."',
            },
            'barril_quebrado': {
                'rotulo': 'Examinar o barril quebrado', 'emoji': '🪵',
                'texto': '🪵 Um barril quebrado, com marcas de unhas por dentro. Melhor não pensar nisso.',
            },
        },
    },
    4: {
        'nome': 'Porta Trancada',
        'objetivo': 'A saída está à sua frente. Use a combinação da carta para abrir o cadeado.',
        'objetos': {
            'cadeado': {
                'rotulo': 'Examinar o cadeado',
                'emoji': '🔒',
                'texto': '🔒 Um cadeado de três rodas numeradas. A carta do baú deve ajudar.',
                'foca_senha': True,
            },
            # ambiente
            'tocha_esquerda': {
                'rotulo': 'Examinar a tocha da esquerda', 'emoji': '🔥',
                'texto': '🔥 O fogo da tocha é frio. Ele não esquenta, só ilumina.',
            },
            'tocha_direita': {
                'rotulo': 'Examinar a tocha da direita', 'emoji': '🔥',
                'texto': '🔥 Quando você chega perto, a chama se inclina na direção do cadeado.',
            },
            'argola': {
                'rotulo': 'Bater a argola da porta', 'emoji': '🚪',
                'texto': '😱 Você bate a argola uma vez... e do outro lado alguém bate TRÊS vezes de volta!',
                'efeito': 'susto',
            },
            'caveira': {
                'rotulo': 'Examinar a caveira na prateleira', 'emoji': '💀',
                'texto': '💀 A caveira está virada para a porta, como se também esperasse a saída.',
            },
            'lanterna': {
                'rotulo': 'Examinar a lanterna', 'emoji': '🏮',
                'texto': '🏮 Uma lanterna acesa sobre o caixote. Ao lado, a vela já derreteu quase toda: o tempo está passando!',
            },
            'barril': {
                'rotulo': 'Examinar o barril', 'emoji': '🛢️',
                'texto': '🛢️ O barril cheira a vinho velho. Uma garrafa vazia está caída ao lado.',
            },
            'livros': {
                'rotulo': 'Examinar a pilha de livros', 'emoji': '📚',
                'texto': '📚 Livros sobre portas e fechaduras. Um deles está aberto: "Toda saída cobra um preço".',
            },
        },
        'senha': {'tamanho': 3, 'rotulo': 'Combinação do cadeado (3 dígitos)',
                  'dica_erro': '❌ O cadeado não abriu! Lembre-se da carta encontrada no baú.',
                  'texto_acerto': '🎉 O cadeado se abre e a luz da lua invade o corredor. VOCÊ ESCAPOU!'},
    },
}

# Duas dicas por cômodo: a primeira orienta, a segunda praticamente entrega.
# 'sem_item' e 'com_item' permitem dicas diferentes conforme o inventário.
DICAS = {
    1: {'sem_item': ['A anotação na estante fala de um retrato. O que haveria atrás dele?',
                     'Clique no retrato da mulher, no centro da parede, para achar a chave.'],
        'com_item': ['Você já tem a chave. A porta trancada fica à direita.'],
        'item': 'chave'},
    2: {'dicas': ['O calendário dá os números e o relógio diz em que ordem usá-los.',
                  'A senha da passagem é ' + SENHA_QUARTO + '.']},
    3: {'sem_item': ['O retrato aponta para algo perto da lamparina: investigue o baú.',
                     'Abra o baú no canto esquerdo, embaixo da lamparina.'],
        'com_item': ['Você já tem a carta. Agora suba a escadaria no fundo do porão.'],
        'item': 'carta'},
    4: {'dicas': ['A combinação está na carta que você encontrou no baú.',
                  'A combinação do cadeado é {codigo_carta}.']},
}

CONQUISTAS = {
    'primeira_fuga': {'nome': 'Primeira Fuga', 'emoji': '🕯️', 'descricao': 'Escapou da mansão pela primeira vez.'},
    'sem_erros':     {'nome': 'Mente Afiada',  'emoji': '🧠', 'descricao': 'Escapou sem errar nenhuma senha.'},
    'relampago':     {'nome': 'Relâmpago',     'emoji': '⚡', 'descricao': 'Escapou em menos de 2 minutos.'},
    'detetive':      {'nome': 'Detetive',      'emoji': '🔎', 'descricao': 'Investigou todos os objetos da mansão.'},
    'sem_dicas':     {'nome': 'Por Conta Própria', 'emoji': '🦉', 'descricao': 'Escapou sem pedir nenhuma dica.'},
}


# ---------------------------------------------------------------
# Sorteio do enigma
# ---------------------------------------------------------------

def sortear_codigo_carta():
    """Sorteia os 3 números da carta do baú (de 1 a 9) para uma nova partida."""
    sorteio = random.SystemRandom()    # aleatório do sistema operacional: imprevisível
    return ''.join(sorteio.choice('123456789') for _ in range(3))


def senha_da_fase(partida, fase):
    if fase == 2:
        return SENHA_QUARTO
    if fase == 4:
        return partida['codigo_carta']
    return None


def variaveis(partida):
    """Valores que preenchem os textos com {chaves}."""
    codigo = partida['codigo_carta']
    return {
        'codigo_carta': codigo,
        'codigo_carta_separado': ' - '.join(codigo),
    }


# ---------------------------------------------------------------
# Funções auxiliares
# ---------------------------------------------------------------

def lista(texto):
    """'chave,carta' -> ['chave', 'carta']"""
    return [parte for parte in texto.split(',') if parte]


def adicionar(texto, valor):
    itens = lista(texto)
    if valor not in itens:
        itens.append(valor)
    return ','.join(itens)


def remover(texto, valor):
    return ','.join(item for item in lista(texto) if item != valor)


def segundos_passados(partida, agora):
    return int((agora - partida['iniciada_em']) / 1000)


def tempo_restante(partida, agora):
    if partida['status'] != 'em_andamento':
        return max(0, TEMPO_LIMITE - (partida['tempo_gasto'] or TEMPO_LIMITE))
    return max(0, TEMPO_LIMITE - segundos_passados(partida, agora))


def calcular_pontos(restante, erros):
    return max(0, restante * PONTOS_POR_SEGUNDO - erros * PENALIDADE_POR_ERRO)


def total_de_objetos():
    return sum(len(fase['objetos']) for fase in FASES.values())


def dicas_da_fase(partida):
    """
    As dicas que valem agora (dependem do cômodo e do inventário) e quantas
    delas o jogador já usou. Cada dica usada é guardada como "fase:etiqueta"
    (ex.: "1:sem_item", "2:dicas"), então dá para contar por lista.
    Retorna (dicas, etiqueta, quantas_usadas).
    """
    regra = DICAS[partida['fase']]
    if 'dicas' in regra:
        etiqueta = 'dicas'
    else:
        etiqueta = 'com_item' if regra['item'] in lista(partida['itens']) else 'sem_item'

    marca = f"{partida['fase']}:{etiqueta}"
    usadas = sum(1 for d in partida['dicas'].split(',') if d == marca)
    return regra[etiqueta], etiqueta, usadas


# ---------------------------------------------------------------
# Ações do jogador
# ---------------------------------------------------------------

def verificar_tempo(partida, agora):
    """Se o tempo acabou, encerra a partida como derrota. Retorna True se acabou."""
    if partida['status'] == 'em_andamento' and segundos_passados(partida, agora) >= TEMPO_LIMITE:
        partida['status'] = 'derrota'
        partida['tempo_gasto'] = TEMPO_LIMITE
        partida['pontos'] = 0
        partida['finalizada_em'] = agora
        return True
    return False


def investigar(partida, objeto_id):
    """Processa o clique em um objeto. Retorna (mensagem, efeito)."""
    fase = FASES[partida['fase']]
    objeto = fase['objetos'].get(objeto_id)

    if objeto is None:
        return 'Não há nada assim por aqui.', None

    partida['pistas'] = adicionar(partida['pistas'], f"{partida['fase']}:{objeto_id}")
    textos = variaveis(partida)

    item_necessario = objeto.get('precisa_item')
    if item_necessario and item_necessario not in lista(partida['itens']):
        return objeto['texto_bloqueado'], 'bloqueado'

    if objeto.get('da_item'):
        partida['itens'] = adicionar(partida['itens'], objeto['da_item'])
        return objeto['texto'].format(**textos), 'item'

    if objeto.get('avanca'):
        if item_necessario:
            partida['itens'] = remover(partida['itens'], item_necessario)   # o item é gasto ao ser usado
        partida['fase'] += 1
        return objeto['texto'], 'avancou'

    if objeto.get('foca_senha'):
        return objeto['texto'], 'senha'

    return objeto['texto'].format(**textos), objeto.get('efeito')


def pedir_dica(partida, agora):
    """
    Dá a próxima dica do cômodo e cobra CUSTO_DICA segundos.
    O custo é cobrado "adiantando" o início da partida: assim o relógio
    oficial, o tempo gasto e a pontuação já consideram a penalidade.
    Retorna (mensagem, efeito).
    """
    dicas, etiqueta, usadas = dicas_da_fase(partida)

    if usadas >= len(dicas):
        return '💡 Você já recebeu todas as dicas deste momento.', 'sem_dica'

    if tempo_restante(partida, agora) <= CUSTO_DICA:
        return '⏳ Não há tempo suficiente para uma dica!', 'sem_dica'

    # Aqui não usamos adicionar(), porque a mesma marca pode se repetir (1ª e 2ª dica)
    marca = f"{partida['fase']}:{etiqueta}"
    partida['dicas'] = f"{partida['dicas']},{marca}" if partida['dicas'] else marca
    partida['iniciada_em'] -= CUSTO_DICA * 1000
    texto = dicas[usadas].format(**variaveis(partida))
    return f'💡 Dica (−{CUSTO_DICA} s): {texto}', 'dica'


def responder(partida, resposta, agora):
    """Confere a senha da fase atual. Retorna (mensagem, efeito)."""
    senha = FASES[partida['fase']].get('senha')

    if senha is None:
        return 'Não há nenhuma senha para digitar aqui.', None

    if resposta != senha_da_fase(partida, partida['fase']):
        partida['erros'] += 1
        return senha['dica_erro'], 'erro'

    if partida['fase'] < FASE_FINAL:
        partida['fase'] += 1
        return senha['texto_acerto'], 'avancou'

    # Última senha certa: vitória!
    gasto = segundos_passados(partida, agora)
    partida['status'] = 'vitoria'
    partida['fase'] = FASE_FINAL + 1
    partida['tempo_gasto'] = gasto
    partida['pontos'] = calcular_pontos(TEMPO_LIMITE - gasto, partida['erros'])
    partida['finalizada_em'] = agora
    return senha['texto_acerto'], 'vitoria'


def conquistas_merecidas(partida, vitorias_anteriores):
    """Lista as conquistas que esta vitória merece."""
    codigos = []
    if vitorias_anteriores == 0:
        codigos.append('primeira_fuga')
    if partida['erros'] == 0:
        codigos.append('sem_erros')
    if partida['tempo_gasto'] < 120:
        codigos.append('relampago')
    if len(lista(partida['pistas'])) >= total_de_objetos():
        codigos.append('detetive')
    if not lista(partida['dicas']):
        codigos.append('sem_dicas')
    return codigos


# ---------------------------------------------------------------
# O que o navegador recebe
# ---------------------------------------------------------------

def estado_publico(partida, agora):
    """
    Monta o JSON da partida para o front-end. Repare que as respostas das
    senhas NÃO são enviadas, só o tamanho e o rótulo do campo.
    """
    estado = {
        'id': partida['id'],
        'jogador': partida['jogador'],
        'status': partida['status'],
        'fase': partida['fase'],
        'total_fases': FASE_FINAL,
        'itens': lista(partida['itens']),
        'erros': partida['erros'],
        'dicas': len(lista(partida['dicas'])),
        'custo_dica': CUSTO_DICA,
        'pontos': partida['pontos'],
        'tempo_limite': TEMPO_LIMITE,
        'tempo_restante': tempo_restante(partida, agora),
        'tempo_gasto': partida['tempo_gasto'],
    }

    if partida['status'] == 'em_andamento':
        fase = FASES[partida['fase']]
        vistas = lista(partida['pistas'])
        dicas, _, usadas = dicas_da_fase(partida)
        estado['dica_disponivel'] = usadas < len(dicas)
        estado['cenario'] = {
            'nome': fase['nome'],
            'objetivo': fase['objetivo'],
            'objetos': [
                {'id': objeto_id, 'rotulo': objeto['rotulo'], 'emoji': objeto['emoji'],
                 'visto': f"{partida['fase']}:{objeto_id}" in vistas}
                for objeto_id, objeto in fase['objetos'].items()
            ],
            'senha': ({'tamanho': fase['senha']['tamanho'], 'rotulo': fase['senha']['rotulo']}
                      if 'senha' in fase else None),
        }

    return estado
