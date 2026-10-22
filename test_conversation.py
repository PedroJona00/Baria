import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import app
from engine.normalizer import normalize
from engine.rules import RuleEngine
from engine.validator import ResponseValidator
from engine.knowledge import KnowledgeBase

class ConversationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.root = Path(self.temp.name)
        (self.root/'data').mkdir()
        for name in ('memoria.json', 'regras.json'):
            (self.root/'data'/name).write_bytes((app.ROOT/'data'/name).read_bytes())
        self.patcher = patch.object(app, 'ROOT', self.root)
        self.patcher.start()
        self.state = {}

    def tearDown(self):
        self.patcher.stop()
        self.temp.cleanup()

    def ask(self, text, prefs=None, action='chat'):
        return app.reply(self.state, text, prefs or {}, action)

    def test_greeting_varies_without_randomness(self):
        one = self.ask('Olá!')
        two = self.ask('Olá!')
        self.assertEqual(one['diagnostics']['intent'], 'greet')
        self.assertNotEqual(one['message'], two['message'])
        self.assertNotIn('drink', one)

    def test_negative_flavor_is_not_positive(self):
        result = self.ask('Não gosto de doce, prefiro cítrico sem álcool')
        self.assertIn('citrico', result['drink']['tags'])
        self.assertNotIn('doce', result['drink']['tags'])
        self.assertEqual(self.state['prefs']['alcool'], 'nao')

    def test_compound_ingredient_negation(self):
        result = self.ask('Quero algo sem leite e café, sem álcool')
        ingredients = normalize(' '.join(i['nome'] for i in result['drink']['ingredientes']))
        self.assertNotIn('leite', ingredients)
        self.assertNotIn('cafe', ingredients)

    def test_typo_and_synonym(self):
        result = self.ask('quero algo refescante sem alcol')
        self.assertFalse(result['drink']['alcool'])
        self.assertIn('refrescante', result['drink']['tags'])
        self.assertTrue(result['diagnostics']['corrections'])
        self.assertEqual(self.ask('quero algo docinho sem álcool')['preferences']['sabor'], 'doce')

    def test_follow_up_and_explanation(self):
        chosen = self.ask('Quero algo refrescante sem álcool')['drink']
        result = self.ask('Como preparar ela?')
        self.assertEqual(result['drink']['id'], chosen['id'])
        self.assertIn(chosen['preparo'], result['message'])
        why = self.ask('Por que escolheu essa?')
        self.assertIn('restrições', why['message'])
        self.assertTrue(why['diagnostics']['rule_trace'])

    def test_follow_up_without_target(self):
        result = self.ask('Como preparar?')
        self.assertNotIn('drink', result)
        self.assertEqual(self.state['task'], 'awaiting_clarification')
        result = self.ask('Mojito')
        self.assertEqual(result['diagnostics']['intent'], 'recipe')
        self.assertIn('Separe', result['message'])

    def test_conflicting_alcohol_asks_then_resolves(self):
        result = self.ask('Quero com álcool e sem álcool')
        self.assertNotIn('drink', result)
        self.assertEqual(self.state['pending']['field'], 'alcool')
        result = self.ask('Sem álcool')
        self.assertFalse(result['drink']['alcool'])
        self.assertNotIn('pending', self.state)

    def test_latest_preference_wins_between_turns(self):
        self.ask('quero algo doce sem álcool')
        result = self.ask('Na verdade, agora prefiro com álcool e amargo')
        self.assertTrue(result['drink']['alcool'])
        self.assertIn('amargo', result['drink']['tags'])
        self.assertTrue(self.state['changes'])

    def test_alternative_does_not_repeat(self):
        first = self.ask('quero algo cítrico sem álcool')['drink']['id']
        second = self.ask('Outra opção')['drink']['id']
        self.assertNotEqual(first, second)
        self.assertFalse(self.ask('Outra opção')['drink']['alcool'])

    def test_describe_does_not_change_alcohol_preference(self):
        self.ask('Quero sem álcool')
        result = self.ask('Mojito sem álcool')
        self.assertEqual(result['preferences']['alcool'], 'nao')
        self.assertEqual(result['drink']['nome'], 'Mojito sem álcool')

    def test_compare_two_drinks_and_one_with_context(self):
        result = self.ask('Compare Mojito e Mojito sem álcool')
        self.assertEqual(result['diagnostics']['intent'], 'compare')
        self.assertIn('Mojito: com álcool', result['message'])
        self.assertIn('Mojito sem álcool: sem álcool', result['message'])
        result = self.ask('Compare com limonada')
        self.assertIn('Limonada', result['message'])

    def test_unknown_logged_without_recommendation(self):
        self.ask('quero sem álcool')
        result = self.ask('florb zzz blarg')
        self.assertEqual(result['diagnostics']['confidence'], 0)
        self.assertNotIn('drink', result)
        event = json.loads((self.root/'data/feedback.jsonl').read_text(encoding='utf-8').splitlines()[-1])
        self.assertEqual(event['category'], 'unrecognized')
        self.assertEqual(event['previous']['intent'], 'recommend')

    def test_feedback_and_rule_suggestion_no_auto_learning(self):
        before = (self.root/'data/regras.json').read_bytes()
        self.ask('quero sem álcool')
        self.ask('Não foi isso que eu pedi')
        self.ask('Sugiro uma regra: use aromas como preferência')
        events = [json.loads(line) for line in (self.root/'data/feedback.jsonl').read_text(encoding='utf-8').splitlines()]
        self.assertEqual([e['category'] for e in events], ['misclassified_intent', 'rule_suggestion'])
        self.assertEqual(before, (self.root/'data/regras.json').read_bytes())

    def test_unsupported_fact_not_invented(self):
        result = self.ask('Quantas calorias tem a Caipirinha?')
        self.assertEqual(result['diagnostics']['intent'], 'unsupported')
        self.assertNotIn('drink', result)

    def test_numbers_dates_and_invalid_date(self):
        result = self.ask('Quero uma bebida sem álcool para 4 pessoas em 25/12/2026')
        self.assertEqual(result['diagnostics']['entities']['dates'], ['2026-12-25'])
        self.assertIn({'value':4.0, 'unit':'pessoas'}, result['diagnostics']['entities']['numbers'])
        self.assertIn('não é válida', self.ask('Quero uma bebida em 31/02/2026')['message'])

    def test_short_and_detailed(self):
        self.ask('Limonada')
        short = self.ask('Receita curta')['message']
        detailed = self.ask('Receita detalhada')['message']
        self.assertLess(len(short), len(detailed))
        self.assertIn('1. Separe', detailed)

    def test_history_bounded_and_reset(self):
        for _ in range(34): self.ask('Oi')
        self.assertEqual(len(self.state['history']), 60)
        self.ask('', action='reset')
        self.assertEqual(self.state, {})

    def test_pending_contribution_question_does_not_save(self):
        self.ask('Limonada')
        self.ask('', action='finish')
        result = self.ask('Como preparar?')
        self.assertTrue(result['adding'])
        self.assertFalse(any(d['contribuicoes'] for d in app.read_memory()['bebidas']))
        self.ask('cancelar')
        self.assertFalse(self.state['adding'])

    def test_inference_chains(self):
        facts, trace = RuleEngine().infer({'alcool':'nao','sabor':'refrescante'})
        self.assertIn('exclude_alcohol', facts)
        self.assertIn('prefer_refreshing_non_alcoholic', facts)
        self.assertEqual(trace, ['restricao_alcool','perfil_sem_alcool'])

    def test_validator_refuses_unknown_or_disallowed_drink(self):
        kb = KnowledgeBase(app.read_memory(), self.root/'data/regras.json')
        with self.assertRaises(ValueError):
            ResponseValidator().validate({'message':'x','drink':kb.drinks[0]}, kb, set())

    def test_invalid_filters_rejected(self):
        with self.assertRaises(ValueError): self.ask('oi', {'alcool':'talvez'})

    def test_context_remembers_preferences(self):
        self.ask('Não gosto de doce, quero cítrico sem álcool')
        result = self.ask('O que eu pedi?')
        self.assertIn('sem álcool', result['message'])
        self.assertIn('perfis excluídos: doce', result['message'])

    def test_conflict_keeps_other_preferences(self):
        self.ask('Quero algo cítrico com álcool e sem álcool')
        result = self.ask('Sem álcool')
        self.assertEqual(result['preferences']['sabor'], 'citrico')

    def test_feedback_during_contribution_is_not_a_fact(self):
        self.ask('Limonada')
        self.ask('', action='finish')
        self.ask('Boa resposta', action='feedback')
        self.assertTrue(self.state['adding'])
        self.assertFalse(any(d['contribuicoes'] for d in app.read_memory()['bebidas']))

    def test_less_sweet_is_excluded(self):
        result = self.ask('Quero algo pouco doce sem álcool')
        self.assertNotIn('doce', result['drink']['tags'])

    def test_alcohol_negation_does_not_negate_flavor(self):
        result = self.ask('Quero sem álcool e doce')
        self.assertFalse(result['drink']['alcool'])
        self.assertIn('doce', result['drink']['tags'])
        self.assertEqual(self.ask('Não quero com álcool')['preferences']['alcool'], 'nao')
