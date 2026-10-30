"""
Apaga todos os jogadores, partidas e conquistas (zera o ranking).
Use antes de apresentar o jogo:  python backend/limpar_banco.py
"""

import database

database.criar_banco()
database.limpar_tudo()

print(f'Banco ({database.nome_do_banco()}) limpo com sucesso!')
