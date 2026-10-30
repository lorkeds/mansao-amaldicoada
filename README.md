# 🎃 Mansão Amaldiçoada

Escape room de Halloween · Hackathon Projeção 2026 · Categoria Avançada.

Você tem **5 minutos** para escapar de uma mansão assombrada: investigue os cômodos, junte pistas e itens e abra os cadeados.

**Jogar:** https://mansao-amaldicoada.onrender.com (o primeiro acesso pode levar ~1 min para o servidor "acordar"). Não há login: basta digitar um nome.

## Equipe

| Integrante | Matrícula |
|---|---|
| João Felipe de Oliveira Damião | 202420666 |
| Gustavo Magalhães Nunes | 202420331 |
| Wesley Angelo Nery | 202420325 |
| Victor Julio de Souza Freire | 202420939 |

## Tecnologias

- **Front-end:** HTML, CSS e JavaScript
- **Back-end:** Python + Flask (API REST). Guarda as senhas, conta o tempo oficial e calcula a pontuação
- **Banco:** PostgreSQL no Render, SQLite no computador
- **Publicação:** Render (`render.yaml`)

## Executar no computador

Requer Python 3.10+.

```bash
pip install -r backend/requirements.txt
python backend/app.py
```

Abra http://127.0.0.1:5000. Sem `DATABASE_URL` o jogo usa SQLite (`database/mansao.db`, criado sozinho); para PostgreSQL, veja `.env.example`.

- Testes: `python -m unittest discover -s backend/tests`
- Zerar o ranking: `python backend/limpar_banco.py`
- Recriar o banco: `database/schema.sql` (PostgreSQL) ou `database/schema_sqlite.sql`

## Estrutura

```
frontend/     index.html, css/, js/, assets/
backend/      app.py (rotas), jogo.py (regras), database.py (SQL), tests/
database/     schema.sql, schema_sqlite.sql
render.yaml   publicação no Render
```

## Créditos

- Trilha: *Shivers in the Shadows*, Victor Lundberg (Epidemic Sound)
- Efeitos e som ambiente: gerados por código (Web Audio API)
- Fonte Creepster (Google Fonts, SIL OFL)
- Imagens dos cenários: *(informar a origem)*
