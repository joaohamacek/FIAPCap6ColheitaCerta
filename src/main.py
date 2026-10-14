"""Colheita Certa: aplicativo de gerenciamento de perdas na colheita de cana."""
import os
import sys
import uuid
from datetime import date, datetime
from getpass import getpass
from pathlib import Path

from arquivos import BASE, DADOS, SAIDAS, ler_json, gravar_json, gravar_texto, registrar_log, ultimos_logs
from validacao import validar, ler_numero, LIMITES
from calculos import indicadores
from relatorios import gerar_relatorio, montar_tabela, dinheiro
import banco_oracle as oracle

PARAMETROS = BASE / 'config' / 'parametros.json'
PENDENTES = DADOS / 'pendentes.json'
CACHE = DADOS / 'cache_oracle.json'
LOG = SAIDAS / 'log_operacoes.txt'
MENU = ('Registrar amostragem', 'Listar amostragens', 'Atualizar amostragem',
        'Excluir amostragem', 'Relatorio', 'Exportar JSON', 'Importar JSON',
        'Sincronizar pendentes', 'Historico', 'Sair')

def log(acao, detalhe): registrar_log(LOG, acao, detalhe)

def carregar_estado():
    parametros = ler_json(PARAMETROS)
    pendentes = ler_json(PENDENTES, [])
    cache = ler_json(CACHE, [])
    estado = {'conn': None, 'tabela': cache[:], 'pendentes': pendentes[:], 'parametros': parametros}
    usuario = os.environ.get('ORACLE_USER') or input('Usuario Oracle (ENTER para modo offline): ').strip()
    if usuario:
        senha = os.environ.get('ORACLE_PASSWORD') or getpass('Senha Oracle: ')
        dsn = os.environ.get('ORACLE_DSN') or input('DSN [oracle.fiap.com.br:1521/ORCL]: ').strip() or 'oracle.fiap.com.br:1521/ORCL'
        try:
            estado['conn'] = oracle.conectar(usuario, senha, dsn)
            oracle.criar_tabela(estado['conn'])
            estado['tabela'] = oracle.listar(estado['conn'])
            gravar_json(CACHE, estado['tabela'])
            print('Conexao Oracle estabelecida.')
        except Exception as exc:
            conn = estado['conn']
            estado['conn'] = None
            if conn is not None:
                try: conn.close()
                except Exception: pass
            estado['tabela'] = cache[:]
            print(f'Falha de conexao: {exc}\nContinuando offline.')
    # Nao exibir duas vezes amostras em cache e pendentes.
    ids = {r['id'] for r in estado['tabela']}
    estado['tabela'].extend(r for r in pendentes if r['id'] not in ids)
    return estado

def persistir_pendentes(estado): gravar_json(PENDENTES, estado['pendentes'])

def entrada_registro(antigo=None):
    antigo = antigo or {}
    campos = [('talhao','Talhao'), ('frente','Frente/equipe'), ('data','Data dd/mm/aaaa'), ('tipo','Tipo 1=MANUAL / 2=MECANICA')]
    while True:
        d = {}
        for chave, titulo in campos:
            padrao = antigo.get(chave, date.today().strftime('%d/%m/%Y') if chave == 'data' else None)
            texto = input(f'{titulo}' + (f' [{padrao}]' if padrao is not None else '') + ': ').strip()
            d[chave] = texto or padrao or ''
        for chave, titulo in [('area_colhida_ha','Area colhida (ha)'), ('produtividade_t_ha','Produtividade (t/ha)'),
                              ('area_amostra_m2','Area amostrada (m2)'), ('massa_perdida_kg','Massa perdida na amostra (kg)')]:
            d[chave] = ler_numero(titulo, chave, antigo.get(chave))
        d['id'] = antigo.get('id', str(uuid.uuid4()))
        try:
            d = validar(d)
            pct = indicadores(d, ler_json(PARAMETROS))['perda_pct']
            if pct > 30 and input(f'ATENCAO: perda de {pct:.1f}%! Confirmar? [s/N]: ').lower() != 's': continue
            return d
        except ValueError as exc: print(f'Erro: {exc}. Digite novamente.\n')

def registrar_amostragem(estado):
    registro = entrada_registro()
    if estado['conn']:
        try: oracle.inserir_lote(estado['conn'], [registro])
        except Exception as exc:
            print(f'Falha no Oracle; salvo offline: {exc}')
            estado['pendentes'].append(registro); persistir_pendentes(estado)
    else:
        estado['pendentes'].append(registro); persistir_pendentes(estado)
    estado['tabela'].append(registro); log('INCLUSAO', registro['id'])
    i = indicadores(registro, estado['parametros'])
    print(f'ID: {registro["id"]}\nPerda: {i["perda_t_ha"]:.2f} t/ha; {i["perda_pct"]:.2f}% | Nivel: {i["nivel"]}')
    print(f'Prejuizo: {dinheiro(i["prejuizo_reais"])} | Economia possivel: {dinheiro(i["economia_possivel_reais"])}')
    print('Recomendacao:', estado['parametros']['recomendacoes'][i['nivel']])

def listar_amostragens(estado):
    linhas = []
    for r in estado['tabela']:
        i = indicadores(r, estado['parametros'])
        linhas.append([r['id'][:8],r['talhao'],r['frente'],r['data'],r['tipo'],f'{i["perda_pct"]:.2f}%',i['nivel'],dinheiro(i['prejuizo_reais'])])
    print(montar_tabela(['ID','Talhao','Frente','Data','Tipo','Perda','Nivel','Prejuizo'], linhas) if linhas else 'Nenhuma amostragem.')

def localizar(estado):
    busca = input('Informe o ID completo ou prefixo: ').strip()
    achados = [r for r in estado['tabela'] if r['id'].startswith(busca)] if busca else []
    if len(achados) != 1: print('ID nao encontrado ou ambiguo.'); return None
    return achados[0]

def atualizar_amostragem(estado):
    if not estado['conn']: print('Atualizacao requer Oracle conectado.'); return
    original = localizar(estado)
    if not original: return
    novo = entrada_registro(original)
    try:
        oracle.atualizar(estado['conn'], novo)
        estado['tabela'][estado['tabela'].index(original)] = novo
        gravar_json(CACHE, oracle.listar(estado['conn']))
        log('ATUALIZACAO', novo['id']); print('Atualizado.')
    except Exception as exc: print(f'Erro Oracle: {exc}')

def excluir_amostragem(estado):
    if not estado['conn']: print('Exclusao requer Oracle conectado.'); return
    original = localizar(estado)
    if not original or input('Confirma exclusao? [s/N]: ').lower() != 's': return
    try:
        oracle.excluir(estado['conn'], original['id']); estado['tabela'].remove(original)
        gravar_json(CACHE, oracle.listar(estado['conn']))
        log('EXCLUSAO', original['id']); print('Excluido.')
    except Exception as exc: print(f'Erro Oracle: {exc}')

def relatorio(estado):
    texto = gerar_relatorio(estado['tabela'], estado['parametros']); print('\n' + texto)
    if input('Salvar TXT? [s/N]: ').lower() == 's':
        caminho = SAIDAS / f'relatorio_{datetime.now():%Y%m%d_%H%M%S}.txt'
        gravar_texto(caminho, texto); log('RELATORIO', str(caminho)); print('Salvo:', caminho)

def exportar(estado):
    registros = [dict(r, indicadores=indicadores(r, estado['parametros'])) for r in estado['tabela']]
    caminho = SAIDAS / f'exportacao_{datetime.now():%Y%m%d_%H%M%S}.json'
    gravar_json(caminho, registros); log('EXPORTACAO', str(caminho)); print('Salvo:', caminho)

def importar(estado):
    nome = input('Caminho JSON [dados/exemplo_amostragens.json]: ').strip() or 'dados/exemplo_amostragens.json'
    caminho = Path(nome)
    if not caminho.is_absolute(): caminho = BASE / caminho
    try:
        dados = ler_json(caminho)
        if not isinstance(dados, list): raise ValueError('JSON deve conter uma lista de registros.')
    except (ValueError, OSError) as exc: print('Erro ao ler:', exc); return
    conhecidos = {r['id'] for r in estado['tabela']}; aceitos, rejeitados = [], 0
    for pos, item in enumerate(dados, start=1):
        try:
            r = validar(item)
            if not r['id']: r['id'] = str(uuid.uuid4())
            if r['id'] in conhecidos: raise ValueError('ID duplicado')
            if indicadores(r, estado['parametros'])['perda_pct'] > 30: raise ValueError('Perda acima de 30%; exige verificacao manual')
            aceitos.append(r); conhecidos.add(r['id'])
        except (ValueError, TypeError, KeyError) as exc:
            rejeitados += 1; print(f'Linha {pos} rejeitada: {exc}')
    # Evitar perda de dados: se falha Oracle, importar todos como pendentes.
    if aceitos and estado['conn']:
        try: oracle.inserir_lote(estado['conn'], aceitos)
        except Exception as exc:
            print('Falha de insercao Oracle; mantendo lote offline:', exc)
            estado['pendentes'].extend(aceitos); persistir_pendentes(estado)
    else:
        estado['pendentes'].extend(aceitos); persistir_pendentes(estado)
    estado['tabela'].extend(aceitos); log('IMPORTACAO', f'{len(aceitos)} aceitos; {rejeitados} rejeitados')
    print(f'Importados: {len(aceitos)} | Rejeitados: {rejeitados}')

def sincronizar(estado):
    if not estado['conn']: print('Conecte-se ao Oracle para sincronizar.'); return
    existentes = {r['id'] for r in oracle.listar(estado['conn'])}
    novos = [r for r in estado['pendentes'] if r['id'] not in existentes]
    try:
        enviados = oracle.inserir_lote(estado['conn'], novos)
        estado['pendentes'].clear(); persistir_pendentes(estado)
        estado['tabela'] = oracle.listar(estado['conn']); gravar_json(CACHE, estado['tabela'])
        log('SINCRONIZACAO', f'{enviados} inseridos no Oracle')
        print(f'Sincronizacao concluida; {enviados} novos registros.')
    except Exception as exc: print('Erro na sincronizacao (pendencias preservadas):', exc)

def historico(estado): print('\n'.join(ultimos_logs(LOG)) or 'Sem historico.')

ACOES = {'1': registrar_amostragem, '2': listar_amostragens, '3': atualizar_amostragem,
         '4': excluir_amostragem, '5': relatorio, '6': exportar,
         '7': importar, '8': sincronizar, '9': historico}

def main():
    estado = carregar_estado()
    try:
        while True:
            print('\n=== COLHEITA CERTA ===')
            for n, nome in enumerate(MENU, start=1): print(f'{n if n<10 else 0}. {nome}')
            escolha = input('Opcao: ').strip()
            if escolha in ('0', '10'): break
            acao = ACOES.get(escolha)
            if acao:
                try: acao(estado)
                except (OSError, ValueError, KeyError) as exc: print('Erro:', exc)
            else: print('Opcao invalida.')
    finally:
        if estado['conn']: estado['conn'].close()

if __name__ == '__main__': main()
