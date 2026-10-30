"""
Testes automáticos da API (usam um banco SQLite temporário, não mexem no real).
Executar na raiz do projeto:  python -m unittest discover -s backend/tests -v
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

# Banco temporário ANTES de importar o app
PASTA_TEMP = tempfile.mkdtemp()
os.environ.pop('DATABASE_URL', None)
os.environ['SQLITE_PATH'] = str(Path(PASTA_TEMP) / 'teste.db')
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import database  # noqa: E402
import jogo      # noqa: E402
from app import app  # noqa: E402


class TestMansao(unittest.TestCase):

    def setUp(self):
        database.limpar_tudo()
        self.cliente = app.test_client()

    def nova_partida(self, nome='Tester'):
        resposta = self.cliente.post('/api/partidas', json={'nome': nome})
        self.assertEqual(resposta.status_code, 201)
        dados = resposta.get_json()
        self.cabecalho = {'X-Partida-Token': dados['token']}
        return dados

    def investigar(self, partida_id, objeto):
        return self.cliente.post(f'/api/partidas/{partida_id}/investigar',
                                 json={'objeto': objeto}, headers=self.cabecalho).get_json()

    def responder(self, partida_id, resposta):
        return self.cliente.post(f'/api/partidas/{partida_id}/responder',
                                 json={'resposta': resposta}, headers=self.cabecalho).get_json()

    def test_nome_invalido_e_recusado(self):
        resposta = self.cliente.post('/api/partidas', json={'nome': '<script>'})
        self.assertEqual(resposta.status_code, 400)

    def senhas(self, partida_id):
        """Senha do quarto (fixa) e combinação sorteada da carta (o navegador nunca recebe isso)."""
        partida = database.buscar_partida(partida_id)
        return jogo.senha_da_fase(partida, 2), jogo.senha_da_fase(partida, 4)

    def dica(self, partida_id):
        return self.cliente.post(f'/api/partidas/{partida_id}/dica', headers=self.cabecalho).get_json()

    def test_senhas_nao_vao_para_o_navegador(self):
        dados = self.nova_partida()
        senha_quarto, codigo_carta = self.senhas(dados['id'])
        self.investigar(dados['id'], 'quadro')
        estado = self.investigar(dados['id'], 'porta')
        self.assertEqual(estado['fase'], 2)
        self.assertNotIn(senha_quarto, str(estado))
        self.assertNotIn(codigo_carta, str(estado))

    def test_senha_do_quarto_e_fixa_e_a_da_carta_muda(self):
        senhas = [self.senhas(self.nova_partida(f'Jogador {i}')['id']) for i in range(15)]
        self.assertEqual({quarto for quarto, _ in senhas}, {'1310'})
        self.assertGreater(len({carta for _, carta in senhas}), 1)

    def test_carta_mostra_a_combinacao_sorteada(self):
        dados = self.nova_partida()
        pid = dados['id']
        self.investigar(pid, 'quadro')
        self.investigar(pid, 'porta')
        self.responder(pid, '1310')
        carta = self.investigar(pid, 'bau')['mensagem']
        self.assertIn(' - '.join(self.senhas(pid)[1]), carta)

    def test_dica_custa_tempo_e_tem_limite(self):
        dados = self.nova_partida()
        pid = dados['id']
        self.investigar(pid, 'quadro')
        self.investigar(pid, 'porta')
        antes = self.cliente.get(f'/api/partidas/{pid}', headers=self.cabecalho).get_json()['tempo_restante']

        primeira = self.dica(pid)
        self.assertEqual(primeira['efeito'], 'dica')
        self.assertLessEqual(primeira['tempo_restante'], antes - jogo.CUSTO_DICA)

        segunda = self.dica(pid)
        self.assertIn(self.senhas(pid)[0], segunda['mensagem'])   # a 2ª dica entrega a senha
        self.assertFalse(segunda['dica_disponivel'])

        terceira = self.dica(pid)
        self.assertEqual(terceira['efeito'], 'sem_dica')
        self.assertEqual(terceira['dicas'], 2)

    def test_dica_muda_depois_de_pegar_o_item(self):
        dados = self.nova_partida()
        pid = dados['id']
        self.dica(pid)
        self.dica(pid)
        self.assertFalse(self.cliente.get(f'/api/partidas/{pid}', headers=self.cabecalho).get_json()['dica_disponivel'])
        estado = self.investigar(pid, 'quadro')                    # pegou a chave: nova dica liberada
        self.assertTrue(estado['dica_disponivel'])
        self.assertIn('porta', self.dica(pid)['mensagem'])

    def test_porta_trancada_sem_chave(self):
        dados = self.nova_partida()
        estado = self.investigar(dados['id'], 'porta')
        self.assertEqual(estado['efeito'], 'bloqueado')
        self.assertEqual(estado['fase'], 1)

    def test_token_errado_e_bloqueado(self):
        dados = self.nova_partida()
        resposta = self.cliente.post(f"/api/partidas/{dados['id']}/investigar",
                                     json={'objeto': 'quadro'}, headers={'X-Partida-Token': 'errado'})
        self.assertEqual(resposta.status_code, 403)

    def test_partida_completa_vai_para_o_ranking(self):
        dados = self.nova_partida('Wesley')
        pid = dados['id']
        senha_quarto, codigo_carta = self.senhas(pid)
        self.investigar(pid, 'quadro')
        self.investigar(pid, 'porta')
        self.assertEqual(self.responder(pid, '0000')['efeito'], 'erro')
        self.assertEqual(self.responder(pid, senha_quarto)['fase'], 3)
        self.assertEqual(self.investigar(pid, 'escadaria')['efeito'], 'bloqueado')
        self.investigar(pid, 'bau')
        self.assertEqual(self.investigar(pid, 'escadaria')['fase'], 4)
        final = self.responder(pid, codigo_carta)

        self.assertEqual(final['status'], 'vitoria')
        self.assertEqual(final['erros'], 1)
        esperado = jogo.calcular_pontos(jogo.TEMPO_LIMITE - final['tempo_gasto'], 1)
        self.assertEqual(final['pontos'], esperado)
        codigos = [c['codigo'] for c in final['conquistas_novas']]
        self.assertIn('primeira_fuga', codigos)
        self.assertIn('sem_dicas', codigos)
        self.assertNotIn('sem_erros', codigos)

        ranking = self.cliente.get('/api/ranking').get_json()
        self.assertEqual(ranking[0]['nome'], 'Wesley')

        perfil = self.cliente.get('/api/jogadores/wesley').get_json()
        self.assertEqual(len(perfil['historico']), 1)

    def test_tempo_esgotado_vira_derrota(self):
        dados = self.nova_partida()
        # Simula que a partida começou há 6 minutos
        database.executar('UPDATE partidas SET iniciada_em = iniciada_em - 360000 WHERE id = ?', (dados['id'],))
        estado = self.investigar(dados['id'], 'quadro')
        self.assertEqual(estado['status'], 'derrota')
        self.assertEqual(estado['pontos'], 0)

    def test_todo_objeto_tem_posicao_no_cenario(self):
        """Cada objeto do jogo.py precisa de uma linha de posição no style.css, senão fica invisível e inalcançável."""
        css = (Path(__file__).resolve().parents[2] / 'frontend' / 'css' / 'style.css').read_text(encoding='utf-8')
        for numero, fase in jogo.FASES.items():
            for objeto_id in fase['objetos']:
                with self.subTest(fase=numero, objeto=objeto_id):
                    self.assertIn(f'.cenario[data-fase="{numero}"] [data-objeto="{objeto_id}"]', css)

    def test_objetos_de_ambiente_dao_pistas_e_sustos(self):
        dados = self.nova_partida()
        pid = dados['id']
        diario = self.investigar(pid, 'mesa')
        self.assertIn('diário', diario['mensagem'])
        self.assertIsNone(diario['efeito'])
        self.assertEqual(self.investigar(pid, 'janela')['efeito'], 'susto')
        self.assertEqual(self.investigar(pid, 'janela')['fase'], 1)       # ambiente não muda de fase

    def test_estatisticas(self):
        self.nova_partida()
        numeros = self.cliente.get('/api/estatisticas').get_json()
        self.assertEqual(numeros['jogadores'], 1)
        self.assertEqual(numeros['partidas'], 1)


if __name__ == '__main__':
    unittest.main()
