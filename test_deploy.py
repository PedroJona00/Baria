import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import app
import web

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
