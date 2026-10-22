"""Testes HTTP pelo handler real, usando transporte em memória (sem portas)."""
import io
import json
import unittest
from unittest.mock import patch
import app

class Socket:
    def __init__(self, request):
        self.input = io.BytesIO(request)
        self.output = bytearray()
    def makefile(self, *args): return self.input
    def sendall(self, data): self.output.extend(data)

class HTTPTests(unittest.TestCase):
    def request(self, method, path, body=None, headers=None):
        data = json.dumps(body or {}).encode()
        headers = {'Host':'127.0.0.1:8000', 'Content-Length':str(len(data)), **(headers or {})}
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
