import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import app
from engine.online import search_drink
from engine.capabilities import quantity

class CapabilityTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.root=Path(self.temp.name)
        (self.root/'data').mkdir()
        for name in ('regras.json','memoria.json'):
            (self.root/'data'/name).write_bytes((app.ROOT/'data'/name).read_bytes())
        self.patch=patch.object(app,'ROOT',self.root); self.patch.start()
        self.state={}
        self.original=(self.root/'data/memoria.json').read_bytes()
    def tearDown(self):
        self.assertEqual(self.original,(self.root/'data/memoria.json').read_bytes())
        self.patch.stop(); self.temp.cleanup()
    def ask(self,text):
        return app.reply(self.state,text,{})
    def test_scale_word_and_context(self):
        self.ask('Como faço uma caipirinha?')
        result=self.ask('Quanto preciso para dez pessoas?')
        self.assertEqual(result['scaled_recipe']['portions'],10)
        self.assertIn('Cachaça: 500 ml',result['message'])
        self.assertIn('Limão: 10 unidade',result['message'])
    def test_fractions(self):
        self.assertEqual(quantity('1/2 xícara',3),'1,5 xícaras')
        self.assertEqual(quantity('1/4 unidade',4),'1 unidade')
        self.assertIn('ajuste ao servir',quantity('a gosto',8))
    def test_scale_missing_target_and_invalid_number(self):
        self.assertNotIn('scaled_recipe',self.ask('Quanto preciso para 5 pessoas?'))
        self.assertEqual(self.ask('Caipirinha')['scaled_recipe']['portions'],5)
        self.assertNotIn('scaled_recipe',self.ask('Caipirinha para 0 pessoas'))
        self.assertNotIn('scaled_recipe',self.ask('Caipirinha para -2 pessoas'))
        self.assertNotIn('scaled_recipe',self.ask('Caipirinha para 2,5 pessoas'))
    def test_substitute_and_restriction(self):
        self.ask('Caipirinha')
        result=self.ask('Posso trocar a cachaça por vodka?')
        self.assertIn('caipiroska',result['message'])
        self.ask('Quero sem álcool')
        result=self.ask('Posso trocar cachaça por vodka na caipirinha?')
        self.assertIn('conflita',result['message'])
    def test_unknown_substitution(self):
        self.ask('Caipirinha')
        self.assertIn('Não tenho uma regra',self.ask('Trocar cachaça por leite?')['message'])
    def test_equipment(self):
        result=self.ask('Como faço sem coqueteleira?')
        self.assertIn('Nunca agite líquidos quentes ou gaseificados',result['message'])
        self.assertIn('peneira',self.ask('Não tenho coador')['message'])
    def test_taste(self):
        self.assertIn('amostra',self.ask('Ficou muito doce')['message'])
        self.assertIn('não remove o álcool',self.ask('Ficou muito forte')['message'])
    def test_occasion_hard_filters(self):
        result=self.ask('O que combina com churrasco sem álcool e sem leite?')
        self.assertEqual(result['diagnostics']['intent'],'occasion')
        self.assertFalse(result['drink']['alcool'])
        self.assertNotIn('leite',' '.join(i['nome'].lower() for i in result['drink']['ingredientes']))
    def test_budget_without_prices_asks(self):
        result=self.ask('Qual drink faço com até R$ 20?')
        self.assertNotIn('estimated_cost',result)
        self.assertIn('Não tenho preços locais',result['message'])
    def test_budget_calculates_and_preserves_context(self):
        self.ask('Caipirinha com orçamento de 20 reais')
        result=self.ask('cachaça = 3; limão = 1,50; açúcar = 0,20; gelo = 0')
        self.assertEqual(result['estimated_cost'],'4.70')
        self.assertEqual(result['drink']['nome'],'Caipirinha')
    def test_budget_over_limit(self):
        self.ask('Caipirinha com orçamento de 2 reais')
        result=self.ask('cachaça = 3; limão = 1; açúcar = 1; gelo = 0')
        self.assertNotIn('estimated_cost',result)
        self.assertIn('acima do limite',result['message'])
    def test_budget_unknown_cost_never_zero(self):
        self.ask('Caipirinha com orçamento de 20 reais')
        result=self.ask('cachaça = 3')
        self.assertNotIn('estimated_cost',result)
        self.assertIn('Limão',result['message'])
    def test_storage_cited_no_shelf_life(self):
        self.ask('Mojito')
        result=self.ask('Posso preparar hoje e servir amanhã?')
        self.assertIn('4 °C',result['message'])
        self.assertIn('não posso garantir',result['message'])
        self.assertTrue(result['sources'][0]['url'].startswith('https://www.fda.gov/'))
    def test_online_dispatch_no_catalog_write(self):
        with patch('engine.capabilities.search_drink',return_value={'message':'Resultado externo','sources':[]}) as lookup:
            result=self.ask('Pesquise na internet sobre Aviation')
            lookup.assert_called_once_with('aviation')
            self.assertEqual(result['message'],'Resultado externo')
    def test_online_failure(self):
        def fail(*args,**kwargs): raise OSError('offline')
        self.assertIn('Não consegui',search_drink('Aviation',fail)['message'])
    def test_online_response(self):
        class Response:
            def __enter__(self): return self
            def __exit__(self,*args): pass
            def read(self,n):
                return json.dumps({'query':{'pages':[{'title':'Aviation (coquetel)','extract':'Um coquetel com gin.','index':1}]}}).encode()
        result=search_drink('Aviation',lambda *a,**k:Response())
        self.assertIn('Um coquetel com gin',result['message'])
        self.assertIn('Nada foi adicionado',result['message'])
    def test_cancel_pending(self):
        self.ask('Qual drink faço com até R$ 20?')
        self.ask('cancelar')
        self.assertNotIn('cap_pending',self.state)
    def test_new_recipe_exits_budget_task(self):
        self.ask('Qual drink faço com até R$ 20?')
        self.ask('Como eu faço limonada?')
        self.assertNotIn('cap_pending',self.state)
    def test_contribution_does_not_capture_equipment_question(self):
        self.ask('Caipirinha')
        self.ask('encerrar')
        self.assertTrue(self.ask('Não tenho coqueteleira')['adding'])
    def test_clarify_taste(self):
        self.ask('Como corrigir o sabor?')
        result=self.ask('doce')
        self.assertEqual(result['diagnostics']['intent'],'taste')
        self.assertIn('amostra',result['message'])
    def test_clarify_substitute(self):
        self.ask('Posso substituir um ingrediente?')
        result=self.ask('cachaça por vodka')
        self.assertIn('caipiroska',result['message'])
    def test_packaged_storage(self):
        self.ask('Whisky')
        result=self.ask('Como guardar?')
        self.assertIn('rótulo',result['message'])
        self.assertNotIn('4 °C',result['message'])
    def test_budget_reference_uses_last_drink(self):
        self.ask('Limonada')
        result=self.ask('Quanto custa essa?')
        self.assertIn('Limonada',result['message'])
    def test_same_turn_substitution_restriction(self):
        result=self.ask('Quero sem álcool. Posso trocar cachaça por vodka na caipirinha?')
        self.assertIn('conflita',result['message'])
    def test_online_rejects_unrelated_page(self):
        class Response:
            def __enter__(self): return self
            def __exit__(self,*args): pass
            def read(self,n):
                return json.dumps({'query':{'pages':[{'title':'Aviação','extract':'Aviation é o transporte por aviões. Um drink.'}]}}).encode()
        result=search_drink('Aviation',lambda *a,**k:Response())
        self.assertNotIn('sources',result)
        self.assertIn('Não encontrei',result['message'])

if __name__=='__main__': unittest.main()
