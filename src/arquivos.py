"""Operacoes de leitura/escrita de TXT e JSON."""
import json
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
DADOS = BASE / 'dados'
SAIDAS = BASE / 'saidas'

def ler_json(caminho, padrao=None):
    arquivo = Path(caminho)
    if not arquivo.exists(): return padrao
    with arquivo.open('r', encoding='utf-8') as f: return json.load(f)

def gravar_json(caminho, conteudo):
    arquivo = Path(caminho); arquivo.parent.mkdir(parents=True, exist_ok=True)
    with arquivo.open('w', encoding='utf-8') as f: json.dump(conteudo, f, ensure_ascii=False, indent=2)

def gravar_texto(caminho, conteudo):
    arquivo = Path(caminho); arquivo.parent.mkdir(parents=True, exist_ok=True)
    with arquivo.open('w', encoding='utf-8') as f: f.write(conteudo)

def registrar_log(caminho, acao, detalhe):
    arquivo = Path(caminho); arquivo.parent.mkdir(parents=True, exist_ok=True)
    with arquivo.open('a', encoding='utf-8') as f:
        f.write(f'{datetime.now():%d/%m/%Y %H:%M:%S} | {acao} | {detalhe}\n')

def ultimos_logs(caminho, quantidade=15):
    arquivo = Path(caminho)
    return arquivo.read_text(encoding='utf-8').splitlines()[-quantidade:] if arquivo.exists() else []
