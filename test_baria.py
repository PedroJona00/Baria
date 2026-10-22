"""Suíte completa do BARIA: conversa, receitas, memória e servidores HTTP/WSGI."""
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
from engine.online import search_drink
from engine.capabilities import quantity
import io
import os
import web


# Preferências e persistência

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


# Interpretação e contexto

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


# Capacidades práticas

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


# Transporte HTTP local

class Socket:
    def __init__(self, request):
        self.input = io.BytesIO(request)
        self.output = bytearray()
    def makefile(self, *args): return self.input
    def sendall(self, data): self.output.extend(data)

class HTTPTests(unittest.TestCase):
    def request(self, method, path, body=None, headers=None):
        data = json.dumps(body or {}).encode()
        headers = {'Host':'127.0.0.1:8000', 'Content-Length':str(len(data)), 'Content-Type':'application/json', **(headers or {})}
        request = f'{method} {path} HTTP/1.1\r\n' + ''.join(f'{k}: {v}\r\n' for k,v in headers.items()) + '\r\n'
        socket = Socket(request.encode() + data)
        with patch.object(app.Handler, 'log_message'):
            app.Handler(socket, ('127.0.0.1', 1234), None)
        head, content = bytes(socket.output).split(b'\r\n\r\n', 1)
        return head.decode(), content

    def test_assets(self):
        for path in ('/', '/app.js', '/style.css', '/api/catalog'):
            head, body = self.request('GET', path)
            self.assertIn('200 OK', head)
            self.assertTrue(body)

    def test_cookie_round_trip(self):
        head, body = self.request('POST','/api/chat',{'message':'quero algo cítrico sem álcool'})
        self.assertIn('200 OK', head)
        result = json.loads(body)
        cookie = next(line.split(': ', 1)[1].split(';')[0] for line in head.splitlines() if line.startswith('Set-Cookie:'))
        head, body = self.request('POST','/api/chat',{'message':'Como preparar ela?'}, {'Cookie':cookie})
        self.assertEqual(json.loads(body)['drink']['id'], result['drink']['id'])
        self.assertEqual(json.loads(body)['diagnostics']['intent'], 'recipe')

    def test_origin_and_schema(self):
        self.assertIn('403', self.request('POST','/api/chat', {'message':'oi'}, {'Origin':'https://example.invalid'})[0])
        self.assertIn('400', self.request('POST','/api/chat', {'message':'oi','preferences':{'alcool':'invalid'}})[0])
        self.assertIn('404', self.request('GET','/../../app.py')[0])


# Hospedagem WSGI

class DeploymentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.addCleanup(self.temp.cleanup)
        self.env = patch.dict(os.environ, {'BARIA_DATA_DIR': self.temp.name,
            'BARIA_PUBLIC_URL': 'https://baria.example', 'BARIA_SECURE_COOKIE': '1',
            'BARIA_STORAGE_MODE': 'persistent'})
        self.env.start()
        self.addCleanup(self.env.stop)
        app.initialize_storage()
        app.SESSIONS.clear()

    def request(self, method='GET', path='/', payload=None, **extra):
        raw = json.dumps(payload or {}).encode()
        environ = {'REQUEST_METHOD': method, 'PATH_INFO': path, 'HTTP_HOST': 'internal:8000',
            'wsgi.url_scheme': 'http', 'wsgi.input': io.BytesIO(raw), 'CONTENT_LENGTH': str(len(raw)),
            'CONTENT_TYPE': 'application/json', 'HTTP_ORIGIN': 'https://baria.example', **extra}
        response = {}
        def start(status, headers):
            response.update(status=int(status.split()[0]), headers=dict(headers))
        response['body'] = b''.join(web.application(environ, start))
        return response

    def test_health_and_static(self):
        self.assertEqual(json.loads(self.request(path='/healthz')['body'])['drinks'], 102)
        self.assertEqual(self.request()['status'], 200)
        self.assertEqual(self.request(path='/../app.py')['status'], 404)
        self.assertEqual(self.request(method='HEAD')['body'], b'')

    def test_https_proxy_and_followup(self):
        result = self.request('POST', '/api/chat', {'message': 'Como faço uma caipirinha?'})
        self.assertEqual(result['status'], 200)
        cookie = result['headers']['Set-Cookie']
        self.assertIn('Secure', cookie)
        self.assertIn('HttpOnly', cookie)
        first = json.loads(result['body'])
        result = self.request('POST', '/api/chat', {'message': 'E os ingredientes dela?'}, HTTP_COOKIE=cookie.split(';')[0])
        self.assertEqual(json.loads(result['body'])['drink']['id'], first['drink']['id'])

    def test_origin_body_and_methods(self):
        self.assertEqual(self.request('POST', '/api/chat', HTTP_ORIGIN='https://evil.example')['status'], 403)
        self.assertEqual(self.request('POST', '/api/chat', CONTENT_LENGTH='12001')['status'], 413)
        self.assertEqual(self.request('POST', '/api/chat', CONTENT_TYPE='text/plain')['status'], 415)
        self.assertEqual(self.request('POST', '/api/chat', {'message': []})['status'], 400)
        self.assertEqual(self.request('DELETE')['status'], 405)

    def test_seed_preserves_runtime_data_and_source(self):
        source = (app.ROOT / 'data/memoria.json').read_bytes()
        app.save_fact('b001', 'Contribuição isolada de teste.')
        app.initialize_storage()
        saved = app.read_memory()['bebidas'][0]['contribuicoes']
        self.assertEqual(saved[-1]['texto'], 'Contribuição isolada de teste.')
        self.assertEqual((app.ROOT / 'data/memoria.json').read_bytes(), source)

    def test_runtime_feedback(self):
        self.request('POST', '/api/chat', {'message': 'não entendeu meu pedido', 'action': 'feedback'})
        self.assertTrue((Path(self.temp.name) / 'feedback.jsonl').exists())

    def test_invalid_catalog_returns_unavailable(self):
        path = Path(self.temp.name) / 'memoria.json'
        path.write_text('{invalid', encoding='utf-8')
        self.assertEqual(self.request(path='/healthz')['status'], 503)
        self.assertEqual(self.request('POST', '/api/chat', {'message': 'oi'})['status'], 503)

    def test_session_expiry_and_limit(self):
        app.SESSIONS['expired'] = {'_seen': -web.SESSION_TTL}
        result = self.request('POST', '/api/chat', {'message': 'oi'}, HTTP_COOKIE='baria=expired')
        self.assertNotIn('expired', app.SESSIONS)
        cookie = result['headers']['Set-Cookie'].split(';')[0]
        next(iter(app.SESSIONS.values()))['_requests'] = [web.time.monotonic()] * 30
        self.assertEqual(self.request('POST', '/api/chat', {'message': 'oi'}, HTTP_COOKIE=cookie)['status'], 429)

    def test_ephemeral_notice_and_contribution(self):
        with patch.dict(os.environ, {'BARIA_STORAGE_MODE': 'ephemeral'}):
            self.assertIn('Demonstração'.encode(), self.request()['body'])
            result = self.request('POST', '/api/chat', {'message': 'Limonada'})
            cookie = result['headers']['Set-Cookie'].split(';')[0]
            result = self.request('POST', '/api/chat', {'action': 'finish'}, HTTP_COOKIE=cookie)
            self.assertIn('apagados', json.loads(result['body'])['message'])
            result = self.request('POST', '/api/chat', {'message': 'Gosto de servir com gelo.'}, HTTP_COOKIE=cookie)
            self.assertIn('apagados', json.loads(result['body'])['message'])


# Cache, validação e compatibilidade dos servidores

class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'data').mkdir()
        for name in ('memoria.json', 'regras.json'):
            (self.root / 'data' / name).write_bytes((app.ROOT / 'data' / name).read_bytes())
        self.root_patch = patch.object(app, 'ROOT', self.root)
        self.root_patch.start()
        self.addCleanup(self.root_patch.stop)
        self.env = patch.dict(os.environ, {'BARIA_DATA_DIR': str(self.root / 'data')})
        self.env.start()
        self.addCleanup(self.env.stop)
        app.CACHE.invalidate()
        self.addCleanup(app.CACHE.invalidate)

    def test_reuses_knowledge_without_rereading_json(self):
        original = Path.read_text
        with patch.object(Path, 'read_text', autospec=True, side_effect=original) as reads:
            first = app.get_knowledge()
            self.assertEqual(reads.call_count, 2)
            self.assertIs(app.get_knowledge(), first)
            app.reply({}, 'Como faço uma caipirinha?', {})
            self.assertEqual(reads.call_count, 2)

    def test_snapshot_and_reply_do_not_expose_cached_data(self):
        snapshot = app.read_memory()
        snapshot['bebidas'].clear()
        result = app.reply({}, 'Como faço uma caipirinha?', {})
        result['drink']['ingredientes'].clear()
        self.assertTrue(app.read_memory()['bebidas'])
        self.assertTrue(app.reply({}, 'Como faço uma caipirinha?', {})['drink']['ingredientes'])

    def test_external_catalog_edit_rebuilds_indexes(self):
        old = app.get_knowledge()
        memory = app.read_memory()
        memory['bebidas'][0]['nome'] = 'Caipirinha de teste'
        path = self.root / 'data/memoria.json'
        replacement = path.with_suffix('.tmp')
        replacement.write_text(json.dumps(memory), encoding='utf-8')
        os.replace(replacement, path)
        current = app.get_knowledge()
        self.assertIsNot(current, old)
        self.assertEqual(current.mentioned('caipirinha de teste'), ['b001'])

    def test_external_rules_edit_changes_interpretation(self):
        old = app.get_knowledge()
        path = self.root / 'data/regras.json'
        rules = json.loads(path.read_text(encoding='utf-8'))
        next(rule for rule in rules['intencoes'] if rule['name'] == 'greet')['patterns'].append('^salutations$')
        path.write_text(json.dumps(rules), encoding='utf-8')
        self.assertIsNot(app.get_knowledge(), old)
        self.assertEqual(app.reply({}, 'salutations', {})['diagnostics']['intent'], 'greet')

    def test_saved_contribution_invalidates_cache(self):
        first = app.get_knowledge()
        self.assertTrue(app.save_fact('b001', 'Contribuição persistida para validar o cache.'))
        self.assertIsNot(app.get_knowledge(), first)
        self.assertIn('Contribuição persistida', app.read_memory()['bebidas'][0]['contribuicoes'][-1]['texto'])

    def test_rejects_malformed_catalog(self):
        from engine.catalog import KnowledgeError, validate_catalog
        for kind in ('duplicate', 'missing', 'alcohol', 'ingredient', 'quantity', 'contribution'):
            with self.subTest(kind=kind):
                memory = app.read_memory()
                drink = memory['bebidas'][0]
                if kind == 'duplicate':
                    memory['bebidas'][1]['id'] = drink['id']
                elif kind == 'missing':
                    del drink['preparo']
                elif kind == 'alcohol':
                    drink['alcool'] = 'sim'
                elif kind == 'ingredient':
                    drink['ingredientes'][0]['nome'] = ''
                elif kind == 'quantity':
                    drink['ingredientes'][0]['quantidade'] = '0 ml'
                else:
                    drink['contribuicoes'] = [{'texto': ''}]
                with self.assertRaises(KnowledgeError):
                    validate_catalog(memory)

    def test_invalid_refresh_does_not_serve_old_catalog(self):
        from engine.catalog import KnowledgeError
        app.get_knowledge()
        (self.root / 'data/memoria.json').write_text('{invalid', encoding='utf-8')
        with self.assertRaises(KnowledgeError):
            app.get_knowledge()

    def test_startup_rejects_invalid_rules(self):
        from engine.catalog import KnowledgeError
        (self.root / 'data/regras.json').write_text('{"intencoes": [{"name": "bad"}]}', encoding='utf-8')
        with self.assertRaises(KnowledgeError):
            app.initialize_storage()


class SharedHTTPTests(unittest.TestCase):
    request = HTTPTests.request
    def test_rejects_unsupported_media_type(self):
        status, _ = self.request('POST', '/api/chat', {'message': 'oi'}, {'Content-Type': 'application/jsonp'})
        self.assertIn('415', status)

    def test_local_health_and_head(self):
        status, body = self.request('GET', '/healthz')
        self.assertIn('200', status)
        self.assertEqual(json.loads(body)['drinks'], 102)
        status, body = self.request('HEAD', '/')
        self.assertIn('200', status)
        self.assertEqual(body, b'')


if __name__ == '__main__':
    unittest.main()
