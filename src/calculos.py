"""Indicadores de perdas de cana calculados sobre amostragem em campo."""

def perda_t_ha(massa_perdida_kg, area_amostra_m2):
    if area_amostra_m2 <= 0: raise ValueError('A area da amostra deve ser positiva.')
    return massa_perdida_kg / area_amostra_m2 * 10

def classificar_nivel(percentual, faixas):
    for limite, nivel in faixas:
        if percentual <= limite: return nivel
    return 'CRITICA'

def indicadores(registro, parametros):
    p_ha = perda_t_ha(registro['massa_perdida_kg'], registro['area_amostra_m2'])
    pct = p_ha / registro['produtividade_t_ha'] * 100
    toneladas = p_ha * registro['area_colhida_ha']
    preco = parametros['atr_kg_por_tonelada'] * parametros['preco_kg_atr_reais']
    meta_ha = parametros['meta_perda_pct'] / 100 * registro['produtividade_t_ha']
    economia = max(0, p_ha - meta_ha) * registro['area_colhida_ha'] * preco
    return {'perda_t_ha': p_ha, 'perda_pct': pct, 'toneladas_perdidas': toneladas,
            'preco_tonelada': preco, 'prejuizo_reais': toneladas * preco,
            'economia_possivel_reais': economia,
            'nivel': classificar_nivel(pct, parametros['faixas'])}
