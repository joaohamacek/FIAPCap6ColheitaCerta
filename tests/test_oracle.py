"""Contratos Oracle simulados; nenhum servidor ou dado real e alterado."""
import contextlib
import io
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import banco_oracle as oracle
import main as app
from arquivos import gravar_json, ler_json

REGISTRO = dict(id='teste-01', talhao='T-01', frente='COLHEDORA-01',
                data='12/10/2026', tipo='MECANICA', area_colhida_ha=10,
                produtividade_t_ha=100, area_amostra_m2=10, massa_perdida_kg=12)


class TestOracle(unittest.TestCase):
    def setUp(self):
        self.conn = MagicMock()
        self.cur = self.conn.cursor.return_value.__enter__.return_value

    def test_conectar_encaminha_credenciais_e_dsn(self):
        with patch('oracledb.connect', return_value=self.conn) as conectar:
            self.assertIs(oracle.conectar('usuario-teste', 'senha-ficticia', 'dsn-teste'), self.conn)
            conectar.assert_called_once_with(user='usuario-teste', password='senha-ficticia', dsn='dsn-teste')

    def test_listar_mapeia_colunas(self):
        self.cur.fetchall.return_value = [tuple(REGISTRO[k] for k in oracle.COLUNAS)]
        self.assertEqual(oracle.listar(self.conn), [REGISTRO])
        self.assertIn('SELECT ID,TALHAO,FRENTE,DATA_COLHEITA', self.cur.execute.call_args.args[0])
        self.conn.commit.assert_not_called()

    def test_crud_usa_binds_e_commit(self):
        for operacao in ('inserir_lote', 'atualizar', 'excluir'):
            with self.subTest(operacao=operacao):
                self.conn.reset_mock()
                self.cur.rowcount = 1
                argumento = [dict(REGISTRO, extra='ignorar')] if operacao == 'inserir_lote' else REGISTRO if operacao == 'atualizar' else "id' OR '1'='1"
                self.assertEqual(getattr(oracle, operacao)(self.conn, argumento), 1)
                chamada = self.cur.executemany if operacao == 'inserir_lote' else self.cur.execute
                sql, binds = chamada.call_args.args
                valores = binds[0] if operacao == 'inserir_lote' else binds
                self.assertEqual(set(re.findall(r':(\w+)', sql)), set(valores))
                self.assertEqual(valores, {'id': argumento} if operacao == 'excluir' else REGISTRO)
                if operacao == 'excluir':
                    self.assertNotIn(argumento, sql)
                self.conn.commit.assert_called_once()
                self.conn.rollback.assert_not_called()

    def test_crud_falha_faz_rollback(self):
        for operacao, argumento in [('inserir_lote', [REGISTRO]), ('atualizar', REGISTRO), ('excluir', REGISTRO['id'])]:
            with self.subTest(operacao=operacao):
                self.conn.reset_mock()
                self.cur.execute.side_effect = RuntimeError('falha simulada')
                self.cur.executemany.side_effect = RuntimeError('falha simulada')
                with self.assertRaisesRegex(RuntimeError, 'falha simulada'):
                    getattr(oracle, operacao)(self.conn, argumento)
                self.conn.rollback.assert_called_once()
                self.conn.commit.assert_not_called()

    def test_lote_vazio_nao_acessa_banco(self):
        self.assertEqual(oracle.inserir_lote(self.conn, []), 0)
        self.conn.cursor.assert_not_called()

    def test_tabela_existente_ignorada_outros_erros_propagados(self):
        self.cur.execute.side_effect = RuntimeError('ORA-00955: name already used')
        oracle.criar_tabela(self.conn)
        self.cur.execute.side_effect = RuntimeError('ORA-01031: insufficient privileges')
        with self.assertRaisesRegex(RuntimeError, 'ORA-01031'):
            oracle.criar_tabela(self.conn)


class TestFallback(unittest.TestCase):
    def setUp(self):
        temporario = tempfile.TemporaryDirectory()
        self.addCleanup(temporario.cleanup)
        self.pasta = Path(temporario.name)
        for nome in ('PENDENTES', 'CACHE', 'LOG'):
            patcher = patch.object(app, nome, self.pasta / nome)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.parametros = ler_json(app.PARAMETROS)
        self.estado = dict(conn=MagicMock(), tabela=[], pendentes=[], parametros=self.parametros)
        saida = contextlib.redirect_stdout(io.StringIO())
        saida.__enter__()
        self.addCleanup(saida.__exit__, None, None, None)

    def test_falhas_inicializacao_mantem_json_e_estado_offline(self):
        for etapa in ('conectar', 'criar_tabela', 'listar'):
            with self.subTest(etapa=etapa):
                gravar_json(app.PENDENTES, [REGISTRO])
                gravar_json(app.CACHE, [])
                conn = MagicMock()
                with patch.dict(os.environ, {'ORACLE_USER': 'teste', 'ORACLE_PASSWORD': 'ficticia', 'ORACLE_DSN': 'teste'}), \
                     patch.object(oracle, 'conectar', return_value=conn) as conectar, \
                     patch.object(oracle, 'criar_tabela') as criar, \
                     patch.object(oracle, 'listar', return_value=[]) as listar:
                    {'conectar': conectar, 'criar_tabela': criar, 'listar': listar}[etapa].side_effect = RuntimeError('falha simulada')
                    estado = app.carregar_estado()
                self.assertIsNone(estado['conn'])
                self.assertEqual(estado['tabela'], [REGISTRO])
                self.assertEqual(ler_json(app.PENDENTES), [REGISTRO])
                self.assertEqual(ler_json(app.CACHE), [])
                if etapa != 'conectar':
                    conn.close.assert_called_once()

    def test_cadastro_falha_preserva_registro_em_json(self):
        with patch.object(app, 'entrada_registro', return_value=REGISTRO), \
             patch.object(oracle, 'inserir_lote', side_effect=RuntimeError('indisponivel')):
            app.registrar_amostragem(self.estado)
        self.assertEqual(ler_json(app.PENDENTES), [REGISTRO])
        self.assertEqual(self.estado['tabela'], [REGISTRO])

    def test_importacao_falha_preserva_lote_em_json(self):
        arquivo = self.pasta / 'importacao.json'
        gravar_json(arquivo, [REGISTRO])
        with patch('builtins.input', return_value=str(arquivo)), \
             patch.object(oracle, 'inserir_lote', side_effect=RuntimeError('indisponivel')):
            app.importar(self.estado)
        self.assertEqual(ler_json(app.PENDENTES), [REGISTRO])
        self.assertEqual(self.estado['tabela'], [REGISTRO])

    def test_sincronizacao_falha_preserva_pendentes(self):
        self.estado['pendentes'] = [REGISTRO]
        gravar_json(app.PENDENTES, [REGISTRO])
        with patch.object(oracle, 'listar', return_value=[]), \
             patch.object(oracle, 'inserir_lote', side_effect=RuntimeError('indisponivel')):
            app.sincronizar(self.estado)
        self.assertEqual(ler_json(app.PENDENTES), [REGISTRO])
        self.assertEqual(self.estado['pendentes'], [REGISTRO])


if __name__ == '__main__':
    unittest.main()
