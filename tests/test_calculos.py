import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from calculos import perda_t_ha, classificar_nivel, indicadores
from validacao import validar

P = {'meta_perda_pct': 5, 'atr_kg_por_tonelada': 127, 'preco_kg_atr_reais': 1.0709,
     'faixas': [[5,'BAIXA'],[10,'MEDIA'],[15,'ALTA']]}
R = {'id':'teste-01','talhao':'t-01','frente':'colhedora-01','data':'12/10/2026',
     'tipo':'2','area_colhida_ha':10,'produtividade_t_ha':100,
     'area_amostra_m2':10,'massa_perdida_kg':12}
class Testes(unittest.TestCase):
    def test_perda_por_hectare(self): self.assertEqual(perda_t_ha(12,10),12)
    def test_perda_percentual(self): self.assertAlmostEqual(indicadores(validar(R),P)['perda_pct'],12)
    def test_prejuizo(self): self.assertAlmostEqual(indicadores(validar(R),P)['prejuizo_reais'],12*10*127*1.0709)
    def test_economia(self): self.assertAlmostEqual(indicadores(validar(R),P)['economia_possivel_reais'],7*10*127*1.0709)
    def test_niveis(self):
        self.assertEqual([classificar_nivel(x,P['faixas']) for x in (5,10,15,16)],['BAIXA','MEDIA','ALTA','CRITICA'])
    def test_valida_tipo(self): self.assertEqual(validar(R)['tipo'],'MECANICA')
    def test_rejeita_talhao(self):
        with self.assertRaises(ValueError): validar(dict(R,talhao='invalido acima de dez'))
    def test_rejeita_perda_maior_producao(self):
        with self.assertRaises(ValueError): validar(dict(R,massa_perdida_kg=150))
if __name__ == '__main__': unittest.main()
