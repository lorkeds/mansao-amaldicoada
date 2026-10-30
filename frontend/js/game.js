/* =============================================================
   Mansão Amaldiçoada — front-end
   O navegador só desenha a tela e envia os cliques para a API.
   Quem decide as regras, confere as senhas, conta o tempo oficial
   e salva tudo no banco é o back-end (backend/app.py + jogo.py).
   ============================================================= */

const API = '/api';
const CHAVE_SESSAO = 'mansao-partida';   // guarda id + token para continuar após recarregar a página
const CHAVE_SOM = 'mansao-som';

const ITENS = {
  chave: '🔑 Chave',
  carta: '📜 Carta',
};

// Atalhos para os elementos da página
const $ = seletor => document.querySelector(seletor);

const telas = {
  inicio: $('#tela-inicio'),
  jogo: $('#tela-jogo'),
  fim: $('#tela-fim'),
};

const cenario = $('#cenario');
const mensagem = $('#mensagem');
const tempo = $('#tempo');
const formSenha = $('#form-senha');
const campoSenha = $('#senha');

let partida = null;        // { id, token }
let estado = null;         // último estado recebido da API
let prazo = 0;             // horário (ms) em que o tempo acaba, sincronizado com o servidor
let relogio = null;
let ocupado = false;       // evita cliques duplos enquanto a API responde
let somLigado = lerPreferencia(CHAVE_SOM) !== 'nao';


/* ---------------------------------------------------------------
   Comunicação com o back-end
   --------------------------------------------------------------- */

async function api(caminho, { metodo = 'GET', corpo } = {}) {
  const cabecalhos = { 'Content-Type': 'application/json' };
  if (partida) cabecalhos['X-Partida-Token'] = partida.token;

  const resposta = await fetch(API + caminho, {
    method: metodo,
    headers: cabecalhos,
    body: corpo ? JSON.stringify(corpo) : undefined,
  });

  const dados = await resposta.json().catch(() => ({}));
  if (!resposta.ok) {
    throw new Error(dados.erro || 'Não foi possível falar com a mansão (servidor).');
  }
  return dados;
}

// Executa uma ação da partida sem permitir cliques repetidos
async function acao(caminho, corpo) {
  if (ocupado || !partida) return;
  ocupado = true;
  try {
    const novoEstado = await api(`/partidas/${partida.id}/${caminho}`, { metodo: 'POST', corpo });
    aplicarEstado(novoEstado);
  } catch (erro) {
    mensagem.textContent = '⚠️ ' + erro.message;
  } finally {
    ocupado = false;
  }
}


/* ---------------------------------------------------------------
   Início da partida
   --------------------------------------------------------------- */

$('#form-inicio').addEventListener('submit', async evento => {
  evento.preventDefault();
  const nome = $('#nome-jogador').value.trim();
  const erroInicio = $('#erro-inicio');
  erroInicio.textContent = '';

  if (nome.length < 2) {
    erroInicio.textContent = 'Digite seu nome (pelo menos 2 letras) antes de entrar na mansão!';
    return;
  }

  $('#iniciar').disabled = true;
  try {
    partida = null;
    const novoEstado = await api('/partidas', { metodo: 'POST', corpo: { nome } });
    partida = { id: novoEstado.id, token: novoEstado.token };
    salvarPreferencia(CHAVE_SESSAO, JSON.stringify(partida), sessionStorage);
    tocar('porta');
    aplicarEstado(novoEstado);
    carregarPerfil(novoEstado.jogador);
    carregarEstatisticas();
  } catch (erro) {
    erroInicio.textContent = erro.message;
  } finally {
    $('#iniciar').disabled = false;
  }
});

$('#jogar-novamente').addEventListener('click', () => {
  partida = null;
  estado = null;
  removerPreferencia(CHAVE_SESSAO, sessionStorage);
  mostrarTela('inicio');
  $('#nome-jogador').focus();
});

// A dica custa tempo: o servidor desconta e devolve o tempo restante já atualizado
$('#dica').addEventListener('click', () => acao('dica'));

$('#desistir').addEventListener('click', () => {
  if (confirm('Desistir agora? A partida conta como derrota.')) {
    acao('desistir');
  }
});


/* ---------------------------------------------------------------
   Desenho da tela a partir do estado que veio da API
   --------------------------------------------------------------- */

function aplicarEstado(novoEstado) {
  const faseAnterior = estado ? estado.fase : null;
  estado = novoEstado;

  if (estado.mensagem) mensagem.textContent = estado.mensagem;
  efeitos(estado.efeito);

  if (estado.status !== 'em_andamento') {
    pararRelogio();
    removerPreferencia(CHAVE_SESSAO, sessionStorage);
    mostrarFim();
    return;
  }

  mostrarTela('jogo');
  desenharFase(faseAnterior !== estado.fase);
  iniciarRelogio(estado.tempo_restante);
}

function desenharFase(trocouDeFase) {
  const { cenario: dadosCenario } = estado;

  $('#titulo-fase').textContent = dadosCenario.nome;
  $('#objetivo-fase').textContent = dadosCenario.objetivo;
  $('#hud-fase').textContent = `${estado.fase} / ${estado.total_fases}`;
  $('#hud-erros').textContent = estado.erros;
  $('#hud-itens').textContent = estado.itens.map(item => ITENS[item] || item).join(' ') || 'vazio';
  $('#barra-progresso').style.width = `${((estado.fase - 1) / estado.total_fases) * 100}%`;

  const botaoDica = $('#dica');
  botaoDica.disabled = !estado.dica_disponivel;
  botaoDica.textContent = estado.dica_disponivel
    ? `💡 Pedir dica (−${estado.custo_dica} s)`
    : '💡 Sem mais dicas por agora';

  cenario.dataset.fase = estado.fase;
  if (trocouDeFase) {
    cenario.classList.remove('transicao');
    void cenario.offsetWidth;            // reinicia a animação
    cenario.classList.add('transicao');
  }

  // Cada objeto vira um botão invisível sobre a imagem. Sem title: o nome
  // não aparece ao passar o mouse (o jogador precisa descobrir o que é),
  // mas o aria-label continua avisando quem usa leitor de tela.
  cenario.innerHTML = '';

  dadosCenario.objetos.forEach(objeto => {
    const area = document.createElement('button');
    area.type = 'button';
    area.className = 'objeto';
    area.dataset.objeto = objeto.id;
    area.setAttribute('aria-label', objeto.rotulo);
    area.addEventListener('click', () => investigar(objeto.id));
    cenario.appendChild(area);
  });

  // Campo de senha só aparece nos cômodos que têm cadeado
  const senha = dadosCenario.senha;
  formSenha.hidden = !senha;
  if (senha) {
    $('#rotulo-senha').textContent = '🔐 ' + senha.rotulo;
    campoSenha.maxLength = senha.tamanho;
    campoSenha.placeholder = '•'.repeat(senha.tamanho);
    if (trocouDeFase) campoSenha.value = '';
  }
}

function investigar(objetoId) {
  acao('investigar', { objeto: objetoId });
}

formSenha.addEventListener('submit', evento => {
  evento.preventDefault();
  const resposta = campoSenha.value.trim();

  if (!/^\d+$/.test(resposta)) {
    mensagem.textContent = '🔢 O cadeado só aceita números.';
    tremer(formSenha);
    return;
  }
  acao('responder', { resposta });
});

// Só deixa digitar números no campo de senha
campoSenha.addEventListener('input', () => {
  campoSenha.value = campoSenha.value.replace(/\D/g, '');
});

function efeitos(efeito) {
  switch (efeito) {
    case 'item':      tocar('item'); break;
    case 'avancou':   tocar('porta'); break;
    case 'bloqueado': tocar('erro'); tremer(cenario); break;
    case 'erro':      tocar('erro'); tremer(formSenha); campoSenha.select(); break;
    case 'senha':     campoSenha.focus(); break;
    case 'dica':      tocar('dica'); break;
    case 'susto':     tocar('susto'); tremer(cenario); break;
    case 'sem_dica':  tocar('erro'); break;
    case 'vitoria':   tocar('vitoria'); break;
    case 'derrota':   tocar('derrota'); break;
  }
}

function tremer(elemento) {
  elemento.classList.remove('tremer');
  void elemento.offsetWidth;
  elemento.classList.add('tremer');
}

function mostrarTela(nome) {
  Object.entries(telas).forEach(([chave, tela]) => {
    tela.hidden = chave !== nome;
  });
}

function mostrarFim() {
  const venceu = estado.status === 'vitoria';

  $('#fim-emoji').textContent = venceu ? '🏆' : '💀';
  $('#fim-titulo').textContent = venceu ? 'Você escapou!' : 'A mansão venceu...';
  $('#fim-texto').textContent = venceu
    ? `Parabéns, ${estado.jogador}! Sua fuga foi registrada no ranking.`
    : `${estado.jogador}, você ficou preso na mansão. Tente de novo!`;
  $('#fim-pontos').textContent = estado.pontos;
  $('#fim-tempo').textContent = formatarTempo(estado.tempo_gasto ?? 0);
  $('#fim-erros').textContent = estado.erros;
  $('#fim-dicas').textContent = estado.dicas;

  const caixa = $('#fim-conquistas');
  caixa.innerHTML = '';
  estado.conquistas_novas.forEach((conquista, indice) => {
    const selo = criarSelo(conquista, 'Nova conquista: ');
    selo.style.animationDelay = `${indice * 0.25}s`;
    caixa.appendChild(selo);
  });

  mostrarTela('fim');
  carregarRanking();
  carregarEstatisticas();
  carregarPerfil(estado.jogador);
}


/* ---------------------------------------------------------------
   Cronômetro (a contagem oficial é do servidor; aqui é só a exibição)
   --------------------------------------------------------------- */

function iniciarRelogio(segundosRestantes) {
  prazo = Date.now() + segundosRestantes * 1000;
  if (relogio) return;
  atualizarRelogio();
  relogio = setInterval(atualizarRelogio, 250);
}

function pararRelogio() {
  clearInterval(relogio);
  relogio = null;
}

function atualizarRelogio() {
  const restante = Math.max(0, Math.ceil((prazo - Date.now()) / 1000));
  tempo.textContent = formatarTempo(restante);
  tempo.parentElement.classList.toggle('urgente', restante <= 60);

  if (restante <= 0) {
    pararRelogio();
    // Pergunta ao servidor: ele confirma que o tempo acabou e grava a derrota
    api(`/partidas/${partida.id}`).then(aplicarEstado).catch(() => {});
  }
}

function formatarTempo(segundos) {
  const minutos = String(Math.floor(segundos / 60)).padStart(2, '0');
  const resto = String(segundos % 60).padStart(2, '0');
  return `${minutos}:${resto}`;
}


/* ---------------------------------------------------------------
   Dados do banco: ranking, estatísticas e histórico
   --------------------------------------------------------------- */

async function carregarRanking() {
  const lista = $('#lista-ranking');
  try {
    const jogadores = await api('/ranking');
    lista.innerHTML = '';

    if (jogadores.length === 0) {
      lista.innerHTML = '<tr><td colspan="4" class="vazio">Ninguém escapou ainda. Seja o primeiro!</td></tr>';
      return;
    }

    const meuNome = (estado?.jogador || $('#nome-jogador').value).trim().toLowerCase();

    jogadores.forEach((jogador, indice) => {
      const linha = document.createElement('tr');
      if (jogador.nome.toLowerCase() === meuNome) linha.classList.add('voce');

      const medalhas = ['🥇', '🥈', '🥉'];
      // textContent (e não innerHTML) impede que um nome malicioso injete código na página
      [medalhas[indice] || indice + 1, jogador.nome, jogador.pontos, formatarTempo(jogador.tempo_gasto)]
        .forEach(valor => {
          const celula = document.createElement('td');
          celula.textContent = valor;
          linha.appendChild(celula);
        });

      lista.appendChild(linha);
    });
  } catch (erro) {
    lista.innerHTML = '<tr><td colspan="4" class="vazio">Ranking indisponível no momento.</td></tr>';
  }
}

async function carregarEstatisticas() {
  try {
    const numeros = await api('/estatisticas');
    document.querySelectorAll('#estatisticas dd').forEach(dd => {
      dd.textContent = numeros[dd.dataset.campo];
    });
  } catch (erro) {
    console.error('Erro ao carregar estatísticas:', erro);
  }
}

async function carregarPerfil(nome) {
  try {
    const perfil = await api('/jogadores/' + encodeURIComponent(nome));
    $('#perfil').hidden = false;
    $('#titulo-perfil').textContent = `🕯️ Histórico de ${perfil.nome}`;

    const conquistas = $('#perfil-conquistas');
    conquistas.innerHTML = '';
    perfil.conquistas.forEach(conquista => conquistas.appendChild(criarSelo(conquista)));
    if (perfil.conquistas.length === 0) {
      conquistas.textContent = `Conquistas: 0 de ${perfil.todas_conquistas}`;
    }

    const historico = $('#perfil-historico');
    historico.innerHTML = '';
    perfil.historico.forEach(jogada => {
      const item = document.createElement('li');
      const resultado = document.createElement('span');
      const detalhe = document.createElement('span');
      resultado.className = jogada.status;
      resultado.textContent = jogada.status === 'vitoria' ? '🏆 Escapou' : `💀 Preso no cômodo ${jogada.fase}`;
      detalhe.textContent = jogada.status === 'vitoria'
        ? `${jogada.pontos} pts · ${formatarTempo(jogada.tempo_gasto)}`
        : formatarTempo(jogada.tempo_gasto ?? 0);
      item.append(resultado, detalhe);
      historico.appendChild(item);
    });
  } catch (erro) {
    $('#perfil').hidden = true;   // jogador novo, ainda sem histórico
  }
}

function criarSelo(conquista, prefixo = '') {
  const selo = document.createElement('span');
  selo.className = 'selo';
  selo.title = conquista.descricao;
  selo.textContent = `${conquista.emoji} ${prefixo}${conquista.nome}`;
  return selo;
}


/* ---------------------------------------------------------------
   Sons (gerados pelo próprio navegador com a Web Audio API,
   então não há arquivo de áudio de terceiros nem problema de licença)
   --------------------------------------------------------------- */

let audio = null;

function tocar(tipo) {
  if (!somLigado) return;
  try {
    audio = audio || new AudioContext();
    const notas = {
      item:    [[660, 0, .12], [990, .12, .2]],
      dica:    [[440, 0, .15], [554, .12, .15], [659, .24, .3]],
      susto:   [[880, 0, .25], [622, .05, .3], [466, .1, .5], [233, .15, .7]],
      porta:   [[110, 0, .5], [82, .25, .6]],
      erro:    [[160, 0, .18], [120, .18, .25]],
      vitoria: [[523, 0, .15], [659, .15, .15], [784, .3, .15], [1047, .45, .4]],
      derrota: [[220, 0, .4], [196, .4, .4], [147, .8, .9]],
    }[tipo] || [];

    notas.forEach(([frequencia, inicio, duracao]) => {
      const oscilador = audio.createOscillator();
      const volume = audio.createGain();
      const t = audio.currentTime + inicio;
      oscilador.type = tipo === 'porta' || tipo === 'derrota' ? 'sawtooth' : 'triangle';
      oscilador.frequency.value = frequencia;
      volume.gain.setValueAtTime(.12, t);
      volume.gain.exponentialRampToValueAtTime(.001, t + duracao);
      oscilador.connect(volume).connect(audio.destination);
      oscilador.start(t);
      oscilador.stop(t + duracao);
    });
  } catch (erro) {
    // navegador sem suporte a áudio: o jogo continua sem som
  }
}


/* ---------------------------------------------------------------
   Som ambiente: vento constante + rangidos de madeira de vez em quando.
   Tudo sintetizado aqui, sem nenhum arquivo de áudio.
   --------------------------------------------------------------- */

let ambiente = null;   // { saida, fontes, timer } enquanto estiver tocando

function iniciarAmbiente() {
  if (ambiente || !somLigado) return;
  try {
    audio = audio || new AudioContext();
    if (audio.state === 'suspended') audio.resume();
    const agora = audio.currentTime;

    // Volume geral do ambiente, que sobe devagar (2 s) para não assustar
    const saida = audio.createGain();
    saida.gain.setValueAtTime(0, agora);
    saida.gain.linearRampToValueAtTime(1, agora + 2);
    saida.connect(audio.destination);

    // VENTO: 2 segundos de ruído branco (números aleatórios) tocando em loop...
    const tamanho = audio.sampleRate * 2;
    const buffer = audio.createBuffer(1, tamanho, audio.sampleRate);
    const amostras = buffer.getChannelData(0);
    for (let i = 0; i < tamanho; i++) amostras[i] = Math.random() * 2 - 1;
    const ruido = audio.createBufferSource();
    ruido.buffer = buffer;
    ruido.loop = true;

    // ...passando por um filtro que deixa só uma faixa de frequências (som de "ssshhh" grave)
    const filtro = audio.createBiquadFilter();
    filtro.type = 'bandpass';
    filtro.frequency.value = 400;
    filtro.Q.value = 0.8;

    const volumeVento = audio.createGain();
    volumeVento.gain.value = 0.05;

    // Dois osciladores bem lentos (LFO) mexem no tom e no volume: o vento "sopra" em rajadas
    const rajadaTom = audio.createOscillator();
    rajadaTom.frequency.value = 0.13;                 // uma volta a cada ~8 s
    const profundidadeTom = audio.createGain();
    profundidadeTom.gain.value = 250;                 // o filtro varia entre 150 e 650 Hz
    rajadaTom.connect(profundidadeTom).connect(filtro.frequency);

    const rajadaVolume = audio.createOscillator();
    rajadaVolume.frequency.value = 0.07;              // uma volta a cada ~14 s
    const profundidadeVolume = audio.createGain();
    profundidadeVolume.gain.value = 0.03;
    rajadaVolume.connect(profundidadeVolume).connect(volumeVento.gain);

    ruido.connect(filtro).connect(volumeVento).connect(saida);
    ruido.start();
    rajadaTom.start();
    rajadaVolume.start();

    ambiente = { saida, fontes: [ruido, rajadaTom, rajadaVolume], timer: null };
    agendarRangido();
  } catch (erro) {
    ambiente = null;   // sem suporte a áudio: segue sem ambiente
  }
}

// O próximo rangido acontece entre 6 e 15 segundos depois do anterior
function agendarRangido() {
  ambiente.timer = setTimeout(() => {
    if (!ambiente) return;
    rangido();
    agendarRangido();
  }, 6000 + Math.random() * 9000);
}

// Rangido de madeira: um tom grave que sobe e desce, "tremido" bem rápido
function rangido() {
  const t = audio.currentTime;
  const base = 90 + Math.random() * 60;

  const tom = audio.createOscillator();
  tom.type = 'sawtooth';
  tom.frequency.setValueAtTime(base, t);
  tom.frequency.linearRampToValueAtTime(base * (1.3 + Math.random() * 0.5), t + 0.6);
  tom.frequency.linearRampToValueAtTime(base * 0.9, t + 1.2);

  const volume = audio.createGain();
  volume.gain.setValueAtTime(0, t);
  volume.gain.linearRampToValueAtTime(0.035, t + 0.15);
  volume.gain.linearRampToValueAtTime(0, t + 1.3);

  // O "tremido" (18 a 28 vezes por segundo) é o que faz parecer madeira rangendo
  const tremido = audio.createOscillator();
  tremido.frequency.value = 18 + Math.random() * 10;
  const forcaTremido = audio.createGain();
  forcaTremido.gain.value = 0.02;
  tremido.connect(forcaTremido).connect(volume.gain);

  const filtro = audio.createBiquadFilter();
  filtro.type = 'bandpass';
  filtro.frequency.value = 700;
  filtro.Q.value = 3;

  tom.connect(filtro).connect(volume).connect(ambiente.saida);
  tom.start(t);
  tremido.start(t);
  tom.stop(t + 1.4);
  tremido.stop(t + 1.4);
}

function pararAmbiente() {
  if (!ambiente) return;
  const { saida, fontes, timer } = ambiente;
  ambiente = null;
  clearTimeout(timer);

  // Abaixa o volume em 0,8 s e só depois desliga tudo
  const t = audio.currentTime;
  saida.gain.cancelScheduledValues(t);
  saida.gain.setValueAtTime(saida.gain.value, t);
  saida.gain.linearRampToValueAtTime(0, t + 0.8);
  setTimeout(() => {
    fontes.forEach(fonte => fonte.stop());
    saida.disconnect();
  }, 900);
}

/* ---------------------------------------------------------------
   Trilha sonora: arquivo frontend/assets/audio/trilha.mp3 num <audio>
   invisível, com "loop" (recomeça sozinho quando acaba).
   --------------------------------------------------------------- */

const trilha = $('#trilha');
trilha.volume = 0.35;          // de fundo, abaixo dos efeitos
let trilhaIniciada = false;    // a trilha começa sozinha só uma vez, no primeiro clique

function tocarTrilha() {
  // play() devolve uma Promise; se o arquivo não existir, só não toca (o jogo segue normal)
  if (somLigado) trilha.play().catch(() => {});
}

function pararTrilha() {
  trilha.pause();
}

// O navegador só deixa tocar som depois de uma interação do jogador,
// então o ambiente e a trilha começam no primeiro clique/toque/tecla na página.
function aoInteragir() {
  iniciarAmbiente();
  if (!trilhaIniciada && somLigado) {
    trilhaIniciada = true;
    tocarTrilha();
  }
}
document.addEventListener('pointerdown', aoInteragir);
document.addEventListener('keydown', aoInteragir);

const botaoSom = $('#botao-som');
function atualizarBotaoSom() {
  botaoSom.textContent = somLigado ? '🔊' : '🔇';
  botaoSom.setAttribute('aria-pressed', String(somLigado));
}
botaoSom.addEventListener('click', () => {
  somLigado = !somLigado;
  salvarPreferencia(CHAVE_SOM, somLigado ? 'sim' : 'nao');
  atualizarBotaoSom();
  if (somLigado) {
    iniciarAmbiente();
    trilhaIniciada = true;
    tocarTrilha();
  } else {
    pararAmbiente();
    pararTrilha();
  }
});


/* ---------------------------------------------------------------
   Armazenamento local (pode falhar em aba anônima, por isso o try)
   --------------------------------------------------------------- */

function lerPreferencia(chave, armazenamento = localStorage) {
  try { return armazenamento.getItem(chave); } catch { return null; }
}
function salvarPreferencia(chave, valor, armazenamento = localStorage) {
  try { armazenamento.setItem(chave, valor); } catch { /* sem armazenamento */ }
}
function removerPreferencia(chave, armazenamento = localStorage) {
  try { armazenamento.removeItem(chave); } catch { /* sem armazenamento */ }
}


/* ---------------------------------------------------------------
   Ao abrir a página
   --------------------------------------------------------------- */

async function retomarPartida() {
  const salva = lerPreferencia(CHAVE_SESSAO, sessionStorage);
  if (!salva) return;

  try {
    partida = JSON.parse(salva);
    const atual = await api(`/partidas/${partida.id}`);
    if (atual.status === 'em_andamento') {
      $('#nome-jogador').value = atual.jogador;
      aplicarEstado({ ...atual, mensagem: '🕯️ Você voltou para a mansão. O relógio não parou...' });
      carregarPerfil(atual.jogador);
    } else {
      partida = null;
      removerPreferencia(CHAVE_SESSAO, sessionStorage);
    }
  } catch (erro) {
    partida = null;
    removerPreferencia(CHAVE_SESSAO, sessionStorage);
  }
}

atualizarBotaoSom();
carregarRanking();
carregarEstatisticas();
retomarPartida();
