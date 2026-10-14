-- A aplicacao cria T_PERDAS_COLHEITA automaticamente na primeira conexao.
-- Consulta de apoio depois da criacao:
SELECT TIPO, COUNT(*) AS AMOSTRAS, SUM(AREA_COLHIDA_HA) AS AREA_HA
FROM T_PERDAS_COLHEITA GROUP BY TIPO;
