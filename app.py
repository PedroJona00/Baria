"""BARIA: execução local, sessões e acesso protegido à memória JSON."""
import copy
import json
import os
import sys
import threading
import unicodedata
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import config
from engine.catalog import CatalogCache, normalize_empty_contributions, validate_catalog

ROOT = Path(__file__).resolve().parent
LOCK = threading.RLock()
SESSIONS = {}
CACHE = CatalogCache()


def norm(value):
    return ''.join(char for char in unicodedata.normalize('NFD', value.lower())
                   if unicodedata.category(char) != 'Mn')


def data_dir():
    return config.data_directory(ROOT)


def get_knowledge():
    return CACHE.knowledge(data_dir() / 'memoria.json', ROOT / 'data/regras.json')


def initialize_storage():
    """Cria apenas o catálogo inicial e valida os dados antes de atender."""
    with LOCK:
        folder = data_dir()
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / 'memoria.json'
        if not path.exists():
            seed = (ROOT / 'data/memoria.json').read_bytes()
            memory = json.loads(seed)
            normalize_empty_contributions(memory)
            validate_catalog(memory)
            temporary = path.with_suffix('.tmp')
            temporary.write_bytes(seed)
            os.replace(temporary, path)
        get_knowledge()


def read_memory():
    return CACHE.snapshot(data_dir() / 'memoria.json')


def save_fact(drink_id, text):
    with LOCK:
        memory = read_memory()
        drink = next(drink for drink in memory['bebidas'] if drink['id'] == drink_id)
        if any(norm(fact['texto']) == norm(text) for fact in drink['contribuicoes']):
            return False
        drink['contribuicoes'].append({
            'texto': text,
            'origem': 'usuario',
            'verificada': False,
            'data': datetime.now(timezone.utc).isoformat(),
        })
        validate_catalog(memory)
        path = data_dir() / 'memoria.json'
        temporary = path.with_suffix('.tmp')
        temporary.write_text(json.dumps(memory, ensure_ascii=False, indent=2), encoding='utf-8')
        os.replace(temporary, path)
        CACHE.invalidate()
        return True


def reply(session, text, prefs, action='chat'):
    from engine.conversation import ConversationEngine
    engine = ConversationEngine(
        ROOT, read_memory, save_fact, data_dir() / 'feedback.jsonl', get_knowledge,
    )
    # Respostas entregues a chamadores não podem alterar o catálogo em cache.
    return copy.deepcopy(engine.reply(session, text, prefs, action))


class Handler(BaseHTTPRequestHandler):
    """Adapta o HTTP local à aplicação WSGI compartilhada com o Waitress."""

    def dispatch(self):
        from web import application
        environ = {
            'REQUEST_METHOD': self.command,
            'PATH_INFO': self.path.split('?', 1)[0],
            'wsgi.url_scheme': 'http',
            'wsgi.input': self.rfile,
            'CONTENT_LENGTH': self.headers.get('Content-Length', '0'),
            'CONTENT_TYPE': self.headers.get('Content-Type', ''),
            'HTTP_HOST': self.headers.get('Host', ''),
            'HTTP_ORIGIN': self.headers.get('Origin', ''),
            'HTTP_COOKIE': self.headers.get('Cookie', ''),
        }

        def start_response(status, headers):
            self.send_response(int(status.split()[0]))
            for name, value in headers:
                self.send_header(name, value)
            self.end_headers()

        for chunk in application(environ, start_response, runtime=sys.modules[__name__]):
            self.wfile.write(chunk)

    do_GET = do_HEAD = do_POST = do_PUT = do_DELETE = do_OPTIONS = dispatch


if __name__ == '__main__':
    import argparse
    host, port = config.server_address()
    parser = argparse.ArgumentParser(description='BARIA — seu bartender digital')
    parser.add_argument('--port', type=int, default=port)
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error('A porta precisa estar entre 1 e 65535.')
    initialize_storage()
    print(f'BARIA disponível em http://{host}:{args.port}', flush=True)
    ThreadingHTTPServer((host, args.port), Handler).serve_forever()
