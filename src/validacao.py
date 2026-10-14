"""Validacao de informacoes digitadas e importadas."""
import math
import re
import unicodedata
from datetime import date, datetime

TIPOS_COLHEITA = ('MANUAL', 'MECANICA')
LIMITES = {'area_colhida_ha': (0.1, 5000), 'produtividade_t_ha': (20, 200),
           'area_amostra_m2': (1, 100), 'massa_perdida_kg': (0, 2000)}
CAMPOS_NUMERICOS = tuple(LIMITES)

def normalizar(texto):
    return ''.join(c for c in unicodedata.normalize('NFKD', str(texto)) if not unicodedata.combining(c)).upper().strip()

def validar(registro):
    d = dict(registro)
    talhao = normalizar(d.get('talhao', ''))
    if not re.fullmatch(r'[A-Z0-9-]{1,10}', talhao): raise ValueError('Talhao: use letras, numeros e hifen (ate 10 caracteres).')
    d['talhao'] = talhao
    frente = normalizar(d.get('frente', ''))
    if not re.fullmatch(r'[A-Z0-9 -]{1,30}', frente): raise ValueError('Frente: use ate 30 caracteres alfanumericos, espacos ou hifen.')
    d['frente'] = frente
    tipo = normalizar(d.get('tipo', ''))
    tipo = {'1': 'MANUAL', '2': 'MECANICA'}.get(tipo, tipo)
    if tipo not in TIPOS_COLHEITA: raise ValueError('Tipo deve ser MANUAL ou MECANICA.')
    d['tipo'] = tipo
    try: dia = datetime.strptime(str(d.get('data', '')), '%d/%m/%Y').date()
    except ValueError: raise ValueError('Data invalida: use dd/mm/aaaa.')
    if not (date(2000, 1, 1) <= dia <= date.today()): raise ValueError('Data fora do intervalo entre 2000 e hoje.')
    d['data'] = dia.strftime('%d/%m/%Y')
    for campo, (minimo, maximo) in LIMITES.items():
        try: numero = float(str(d.get(campo, '')).replace(',', '.'))
        except (ValueError, TypeError): raise ValueError(f'{campo}: informe um numero valido.')
        if not math.isfinite(numero) or not minimo <= numero <= maximo:
            raise ValueError(f'{campo}: deve estar entre {minimo} e {maximo}.')
        d[campo] = numero
    perda = d['massa_perdida_kg'] / d['area_amostra_m2'] * 10
    if perda > d['produtividade_t_ha'] + 1e-9: raise ValueError('A perda calculada nao pode superar a produtividade.')
    d['id'] = str(d.get('id', '')).strip()
    return d

def ler_numero(mensagem, campo, padrao=None):
    minimo, maximo = LIMITES[campo]
    while True:
        valor = input(f'{mensagem}' + (f' [{padrao}]' if padrao is not None else '') + ': ').strip()
        if not valor and padrao is not None: return float(padrao)
        try:
            numero = float(valor.replace(',', '.'))
            if math.isfinite(numero) and minimo <= numero <= maximo: return numero
        except ValueError: pass
        print(f'Valor invalido. Informe um numero entre {minimo} e {maximo}.')
