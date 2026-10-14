"""Relatorios tabulares e rankings de frentes/talhoes."""
from collections import defaultdict
from calculos import indicadores, classificar_nivel

def dinheiro(n): return 'R$ ' + f'{n:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')

def montar_tabela(cabecalhos, linhas):
    linhas = [[str(x) for x in linha] for linha in linhas]
    larguras = [max(len(str(h)), *(len(l[i]) for l in linhas)) for i, h in enumerate(cabecalhos)]
    formato = ' | '.join('{:<%d}' % n for n in larguras)
    return '\n'.join([formato.format(*cabecalhos), '-+-'.join('-'*n for n in larguras)] + [formato.format(*l) for l in linhas])

def imprimir(linhas):
    print('\n'.join(linhas))

def agregados(registros, parametros, campo):
    totais = defaultdict(lambda: {'amostras': 0, 'area': 0, 'perdidas': 0, 'previstas': 0, 'prejuizo': 0, 'economia': 0})
    for r in registros:
        i = indicadores(r, parametros); t = totais[r[campo]]
        t['amostras'] += 1; t['area'] += r['area_colhida_ha']
        t['perdidas'] += i['toneladas_perdidas']
        t['previstas'] += r['produtividade_t_ha'] * r['area_colhida_ha']
        t['prejuizo'] += i['prejuizo_reais']; t['economia'] += i['economia_possivel_reais']
    for t in totais.values():
        t['pct'] = t['perdidas'] / t['previstas'] * 100 if t['previstas'] else 0
        t['nivel'] = classificar_nivel(t['pct'], parametros['faixas'])
    return sorted(totais.items(), key=lambda x: x[1]['pct'], reverse=True)

def gerar_relatorio(registros, parametros):
    if not registros: return 'Nenhuma amostragem registrada.'
    partes = ['COLHEITA CERTA - RELATORIO DE PERDAS', '='*78]
    i = [indicadores(r, parametros) for r in registros]
    perdas = sum(x['toneladas_perdidas'] for x in i)
    producao = sum(r['area_colhida_ha'] * r['produtividade_t_ha'] for r in registros)
    partes += [f'AMOSTRAS: {len(registros)} | AREA: {sum(r["area_colhida_ha"] for r in registros):,.1f} ha',
              f'PERDA TOTAL: {perdas:,.2f} t | PERDA PONDERADA: {perdas/producao*100:.2f}%',
              f'PREJUIZO: {dinheiro(sum(x["prejuizo_reais"] for x in i))}',
              f'ECONOMIA POSSIVEL ATE META: {dinheiro(sum(x["economia_possivel_reais"] for x in i))}']
    for campo, titulo in [('tipo','COMPARACAO MANUAL X MECANICA'), ('frente','RANKING DAS FRENTES'), ('talhao','RANKING DOS TALHOES')]:
        linhas = []
        for nome, t in agregados(registros, parametros, campo):
            linhas.append([nome, t['amostras'], f'{t["area"]:.1f}', f'{t["perdidas"]:.2f}', f'{t["pct"]:.2f}%', t['nivel'], dinheiro(t['prejuizo'])])
        partes += ['', titulo, '-'*78, montar_tabela(['Grupo','N','Area ha','Perda t','Perda %','Nivel','Prejuizo'], linhas)]
    frente, total = agregados(registros, parametros, 'frente')[0]
    partes += ['', 'PRIORIDADE DE ACAO', '-'*78,
              f'Priorizar {frente}: {total["pct"]:.2f}% de perdas ({total["nivel"]}), prejuizo {dinheiro(total["prejuizo"])}.',
              f'Economia potencial estimada: {dinheiro(total["economia"])}.',
              parametros['recomendacoes'][total['nivel']]]
    return '\n'.join(partes)
