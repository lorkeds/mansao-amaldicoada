# 🎃 Mansão Amaldiçoada

Escape room de Halloween para o **Hackathon Projeção 2026 — Categoria Avançada (Veteranos)**.

Você ficou preso numa mansão assombrada e tem **5 minutos** para escapar. Investigue os objetos de quatro cômodos (Biblioteca, Quarto, Porão e Porta Trancada), junte pistas e itens e descubra as senhas dos cadeados. As melhores fugas entram no ranking.

## 🌐 URL pública

**https://mansao-amaldicoada.onrender.com**

No plano gratuito do Render o servidor "dorme" depois de 15 minutos sem acesso: o primeiro acesso pode demorar cerca de 1 minuto.

Para conferir se o servidor e o banco estão no ar, abra `/api/saude`.

## 👥 Equipe

| Integrante | Matrícula |
|---|---|
| João Felipe de Oliveira Damião | 202420666 |
| Gustavo Magalhães Nunes | 202420331 |
| Wesley Angelo Nery | 202420325 |
| Victor Julio de Souza Freire | 202420939 |

## 🧰 Tecnologias

| Camada | Tecnologia |
|---|---|
| Front-end | HTML5, CSS3, JavaScript (sem frameworks), Web Audio API para os efeitos e o som ambiente (vento e rangidos), elemento `<audio>` para a trilha sonora em loop |
| Back-end | Python 3 + Flask (API REST em JSON), Gunicorn em produção |
| Banco de dados | PostgreSQL em produção (Render) · SQLite no computador local |
| Publicação | Render (configurado em `render.yaml`) |

O back-end é o “cérebro” do jogo: guarda as senhas, conta o tempo oficial, confere cada ação, calcula a pontuação e grava tudo no banco (jogadores, partidas, ranking, histórico, conquistas). O navegador só desenha a tela e envia os cliques.

## 🎮 Como jogar

1. Digite seu nome e clique em **Entrar na mansão**.
2. Passe o mouse pelo cenário: onde o cursor virar uma 🔍 lupa, há algo para investigar. Clique para ver o que é.
3. Itens encontrados vão para o inventário; algumas portas precisam deles.
4. Digite as senhas nos cadeados. **A combinação do cadeado final muda a cada partida**: o servidor sorteia os números da carta do baú.
5. Travou? O botão **💡 Pedir dica** dá até duas dicas por momento do jogo, mas cada uma custa **20 segundos**.
6. **Pontuação:** cada segundo que sobrar vale 10 pontos; cada senha errada tira 50.
7. Se o tempo acabar, a mansão vence.

**Credenciais de demonstração:** não são necessárias — o jogo não tem login, basta digitar qualquer nome.

## ▶️ Executar no computador

Requisito: Python 3.10 ou mais novo.

```bash
pip install -r backend/requirements.txt
python backend/app.py
```

Abra http://127.0.0.1:5000. Sem a variável `DATABASE_URL`, o banco SQLite `database/mansao.db` é criado automaticamente.

Para usar PostgreSQL, defina `DATABASE_URL` (veja `.env.example`) antes de iniciar.

### Testes automáticos

```bash
python -m unittest discover -s backend/tests -v
```

### Zerar ranking e histórico

```bash
python backend/limpar_banco.py
```

## 🚀 Publicar no Render

1. Envie o projeto para um repositório no GitHub.
2. No Render: **New → Blueprint** → escolha o repositório.
3. O `render.yaml` cria o banco PostgreSQL e o servidor web e liga os dois pela variável `DATABASE_URL`.
4. Depois do deploy, abra `https://mansao-amaldicoada.onrender.com/api/saude` — deve mostrar `"banco": "postgresql"`.

No plano gratuito o servidor dorme após 15 min sem uso: abra o site alguns minutos antes da avaliação.

## 🗄️ Banco de dados

`database/schema.sql` recria o banco no PostgreSQL (`database/schema_sqlite.sql` é a versão para SQLite). O servidor também cria as tabelas sozinho ao iniciar.

- `jogadores` — cadastro pelo nome
- `partidas` — histórico, progresso salvo, pontuação e tempo
- `conquistas` — conquistas desbloqueadas por jogador

## 📁 Estrutura

```
README.md            este arquivo
render.yaml          publicação no Render
.env.example         variáveis de ambiente (sem dados reais)
apresentacao.pdf     apresentação
pitch.mp4            vídeo do pitch (até 5 min)
frontend/            index.html, css/, js/, assets/img/
backend/             app.py (rotas), jogo.py (regras), database.py (SQL), tests/
database/            schema.sql, schema_sqlite.sql```

## 📜 Recursos de terceiros

- Fonte **Creepster** (Google Fonts) — SIL Open Font License.
- Flask, Gunicorn e psycopg — licenças livres (BSD/MIT/LGPL).
- Efeitos e som ambiente (vento e rangidos de madeira) gerados por código com a Web Audio API, sem arquivos de áudio de terceiros. Liga e desliga pelo botão 🔊.
- Trilha sonora: *Shivers in the Shadows*, de Victor Lundberg (Epidemic Sound), em `frontend/assets/audio/trilha.mp3`. Toca em loop, escondida, e liga e desliga pelo botão 🔊.
- Imagens dos cenários: *(informar a origem — ex.: geradas pela equipe com IA)*.
