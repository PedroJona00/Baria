"""BARIA: assistente local de bebidas, sem dependências externas."""
import json
import os
import re
import secrets
import threading
import unicodedata
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LOCK = threading.RLock()
SESSIONS = {}

def norm(value):
    return ''.join(c for c in unicodedata.normalize('NFD', value.lower()) if unicodedata.category(c) != 'Mn')

def data_dir():
    return Path(os.environ.get('BARIA_DATA_DIR', str(ROOT / 'data')))

def initialize_storage():
    """Seed only an empty runtime directory; never overwrite contributions."""
    with LOCK:
        folder = data_dir()
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / 'memoria.json'
        if not path.exists():
            path.write_bytes((ROOT / 'data/memoria.json').read_bytes())

def read_memory():
    return json.loads((data_dir() / 'memoria.json').read_text(encoding='utf-8'))

def save_fact(drink_id, text):
    with LOCK:
        memory = read_memory()
        drink = next(d for d in memory['bebidas'] if d['id'] == drink_id)
        if any(norm(f['texto']) == norm(text) for f in drink['contribuicoes']):
            return False
        from datetime import datetime, timezone
        drink['contribuicoes'].append({'texto': text, 'origem': 'usuario', 'verificada': False, 'data': datetime.now(timezone.utc).isoformat()})
        path = data_dir() / 'memoria.json'
        temp = path.with_suffix('.tmp')
        temp.write_text(json.dumps(memory, ensure_ascii=False, indent=2), encoding='utf-8')
        os.replace(temp, path)
        return True

def reply(session, text, prefs, action='chat'):
    from engine.conversation import ConversationEngine
    return ConversationEngine(ROOT, read_memory, save_fact, data_dir() / 'feedback.jsonl').reply(session, text, prefs, action)


class Handler(BaseHTTPRequestHandler):
    def send(self, status, data, kind='application/json; charset=utf-8', cookie=None):
        body = json.dumps(data, ensure_ascii=False).encode() if isinstance(data, (dict, list)) else data
        self.send_response(status)
        self.send_header('Content-Type', kind)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('X-Content-Type-Options', 'nosniff')
        if cookie: self.send_header('Set-Cookie', f'baria={cookie}; HttpOnly; SameSite=Strict; Path=/')
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        files = {'/': ('index.html', 'text/html; charset=utf-8'), '/style.css': ('style.css', 'text/css'), '/app.js': ('app.js', 'text/javascript')}
        if self.path == '/api/catalog':
            return self.send(200, read_memory())
        if self.path not in files: return self.send(404, {'error': 'Não encontrado'})
        name, kind = files[self.path]
        self.send(200, (ROOT / 'static' / name).read_bytes(), kind)

    def do_POST(self):
        if self.path != '/api/chat': return self.send(404, {'error': 'Não encontrado'})
        if self.headers.get('Origin') and self.headers['Origin'] != 'http://' + self.headers.get('Host', ''):
            return self.send(403, {'error': 'Origem não permitida'})
        try:
            size = int(self.headers.get('Content-Length', 0))
            if not 0 < size <= 12000: return self.send(413, {'error': 'Mensagem muito grande ou vazia'})
            data = json.loads(self.rfile.read(size))
            if not isinstance(data, dict): raise ValueError()
            message, prefs, action = data.get('message', ''), data.get('preferences', {}), data.get('action', 'chat')
            if not isinstance(message, str) or len(message) > 2000 or not isinstance(prefs, dict) or action not in ('chat', 'reset', 'finish', 'feedback'): raise ValueError()
            cookie = SimpleCookie(self.headers.get('Cookie', ''))
            sid = cookie['baria'].value if 'baria' in cookie else ''
            with LOCK:
                if sid not in SESSIONS:
                    sid = secrets.token_urlsafe(24)
                    if len(SESSIONS) >= 1000: SESSIONS.pop(next(iter(SESSIONS)))
                    SESSIONS[sid] = {}
                result = reply(SESSIONS[sid], message, prefs, action)
            self.send(200, result, cookie=sid)
        except (ValueError, TypeError):
            self.send(400, {'error': 'Dados inválidos'})
        except OSError:
            self.send(500, {'error': 'Não foi possível acessar a memória. Verifique a permissão da pasta data.'})

if __name__ == '__main__':
    initialize_storage()
    import argparse
    parser = argparse.ArgumentParser(description='BARIA — seu bartender digital')
    parser.add_argument('--port', type=int, default=8000)
    args = parser.parse_args()
    print(f'BARIA disponível em http://127.0.0.1:{args.port}', flush=True)
    ThreadingHTTPServer(('127.0.0.1', args.port), Handler).serve_forever()
