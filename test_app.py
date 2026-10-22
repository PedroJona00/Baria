import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import app

class BariaTests(unittest.TestCase):
    def test_alcohol_is_hard_filter(self):
        result = app.reply({}, 'quero algo doce sem álcool', {})
        self.assertFalse(result['drink']['alcool'])
        self.assertIn('doce', result['drink']['tags'])

    def test_exclusions(self):
        result = app.reply({}, 'quero algo cremoso', {'alcool':'nao','evitar':'leite'})
        self.assertFalse(any('leite' in app.norm(i['nome']) for i in result['drink']['ingredientes']))

    def test_named_conflict(self):
        result = app.reply({}, 'Negroni', {'alcool':'nao'})
        self.assertNotIn('drink', result)

    def test_specific_name(self):
        result = app.reply({}, 'Mojito sem álcool', {})
        self.assertEqual(result['drink']['nome'], 'Mojito sem álcool')

    def test_sessions_separate(self):
        one, two = {}, {}
        app.reply(one, 'sem álcool doce', {})
        self.assertNotIn('last', two)
        app.reply(one, '', {}, 'reset')
        self.assertEqual(one, {})

    def test_persist_and_duplicate(self):
        memory = app.read_memory()
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as folder:
            root = Path(folder)
            (root/'data').mkdir()
            (root/'data/memoria.json').write_text(json.dumps(memory), encoding='utf-8')
            (root/'data/regras.json').write_text((app.ROOT/'data/regras.json').read_text(encoding='utf-8'), encoding='utf-8')
            with patch.object(app, 'ROOT', root):
                session = {}
                result = app.reply(session, 'limonada', {'alcool':'nao'})
                drink_id = result['drink']['id']
                self.assertTrue(app.reply(session, '', {}, 'finish')['adding'])
                self.assertTrue(app.reply(session, 'sim', {})['adding'])
                app.reply(session, 'Eu gosto de servir com bastante gelo.', {})
                saved = next(d for d in app.read_memory()['bebidas'] if d['id']==drink_id)
                self.assertEqual(len(saved['contribuicoes']), 1)
                self.assertFalse(saved['contribuicoes'][0]['verificada'])
                self.assertFalse(app.save_fact(drink_id, 'Eu gosto de servir com bastante gelo.'))

if __name__ == '__main__':
    unittest.main()
