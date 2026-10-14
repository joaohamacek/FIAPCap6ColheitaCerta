"""CRUD Oracle usando binds e transacoes. Exige python-oracledb e credenciais validas."""
import json

COLUNAS = ('id', 'talhao', 'frente', 'data', 'tipo', 'area_colhida_ha',
           'produtividade_t_ha', 'area_amostra_m2', 'massa_perdida_kg')

def conectar(usuario, senha, dsn):
    import oracledb
    return oracledb.connect(user=usuario, password=senha, dsn=dsn)

def criar_tabela(conn):
    try:
        with conn.cursor() as cur:
            cur.execute('''CREATE TABLE T_PERDAS_COLHEITA (
            ID VARCHAR2(36) PRIMARY KEY, TALHAO VARCHAR2(10) NOT NULL,
            FRENTE VARCHAR2(30) NOT NULL, DATA_COLHEITA VARCHAR2(10) NOT NULL,
            TIPO VARCHAR2(10) NOT NULL CHECK (TIPO IN ('MANUAL','MECANICA')),
            AREA_COLHIDA_HA NUMBER(12,3) NOT NULL CHECK (AREA_COLHIDA_HA BETWEEN 0.1 AND 5000),
            PRODUTIVIDADE_T_HA NUMBER(12,3) NOT NULL CHECK (PRODUTIVIDADE_T_HA BETWEEN 20 AND 200),
            AREA_AMOSTRA_M2 NUMBER(12,3) NOT NULL CHECK (AREA_AMOSTRA_M2 BETWEEN 1 AND 100),
            MASSA_PERDIDA_KG NUMBER(12,3) NOT NULL CHECK (MASSA_PERDIDA_KG BETWEEN 0 AND 2000))''')
        conn.commit()
    except Exception as exc:
        if getattr(exc, 'code', None) == 955 or 'ORA-00955' in str(exc): return
        raise

def listar(conn):
    with conn.cursor() as cur:
        cur.execute('''SELECT ID,TALHAO,FRENTE,DATA_COLHEITA,TIPO,AREA_COLHIDA_HA,
                          PRODUTIVIDADE_T_HA,AREA_AMOSTRA_M2,MASSA_PERDIDA_KG FROM T_PERDAS_COLHEITA''')
        return [dict(zip(COLUNAS, row)) for row in cur.fetchall()]

def inserir_lote(conn, registros):
    if not registros: return 0
    sql = '''INSERT INTO T_PERDAS_COLHEITA
        (ID,TALHAO,FRENTE,DATA_COLHEITA,TIPO,AREA_COLHIDA_HA,PRODUTIVIDADE_T_HA,AREA_AMOSTRA_M2,MASSA_PERDIDA_KG)
        VALUES (:id,:talhao,:frente,:data,:tipo,:area_colhida_ha,:produtividade_t_ha,:area_amostra_m2,:massa_perdida_kg)'''
    with conn.cursor() as cur:
        try:
            cur.executemany(sql, [{k: r[k] for k in COLUNAS} for r in registros]); conn.commit()
        except Exception:
            conn.rollback(); raise
    return len(registros)

def atualizar(conn, registro):
    with conn.cursor() as cur:
        try:
            cur.execute('''UPDATE T_PERDAS_COLHEITA SET TALHAO=:talhao, FRENTE=:frente,
                DATA_COLHEITA=:data, TIPO=:tipo, AREA_COLHIDA_HA=:area_colhida_ha,
                PRODUTIVIDADE_T_HA=:produtividade_t_ha, AREA_AMOSTRA_M2=:area_amostra_m2,
                MASSA_PERDIDA_KG=:massa_perdida_kg WHERE ID=:id''', {k:registro[k] for k in COLUNAS})
            quantidade = cur.rowcount; conn.commit(); return quantidade
        except Exception: conn.rollback(); raise

def excluir(conn, identificador):
    with conn.cursor() as cur:
        try:
            cur.execute('DELETE FROM T_PERDAS_COLHEITA WHERE ID=:id', {'id': identificador})
            quantidade = cur.rowcount; conn.commit(); return quantidade
        except Exception: conn.rollback(); raise
