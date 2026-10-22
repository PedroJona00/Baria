"""Adaptador WSGI para a mesma lógica usada pelo servidor local."""
import json
import os
import secrets
import time
from http import HTTPStatus
from http.cookies import SimpleCookie, CookieError
import app

SESSION_TTL = 3600
NOTICE = ('Demonstração: conversas são temporárias; curiosidades e feedback podem ser '
          'apagados quando o servidor reiniciar. Não envie dados pessoais.')

def ephemeral():
    return os.environ.get('BARIA_STORAGE_MODE') == 'ephemeral'

def application(environ, start_response):
    method, path = environ.get('REQUEST_METHOD', 'GET'), environ.get('PATH_INFO', '/')
    def respond(status, data, kind='application/json; charset=utf-8', sid=None):
        body = json.dumps(data, ensure_ascii=False).encode() if isinstance(data, (dict, list)) else data
        headers = [('Content-Type', kind), ('Content-Length', str(len(body))),
                   ('X-Content-Type-Options', 'nosniff'), ('Cache-Control', 'no-store'),
                   ('Referrer-Policy', 'same-origin'), ('X-Frame-Options', 'DENY'),
                   ('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'")]
        if sid:
            secure = '; Secure' if os.environ.get('BARIA_SECURE_COOKIE') == '1' else ''
            headers.append(('Set-Cookie', f'baria={sid}; HttpOnly; SameSite=Strict; Path=/; Max-Age={SESSION_TTL}{secure}'))
        start_response(f'{status} {HTTPStatus(status).phrase}', headers)
        return [b'' if method == 'HEAD' else body]
    try:
        if method in ('GET', 'HEAD'):
            if path == '/healthz':
                return respond(200, {'status': 'ok', 'drinks': len(app.read_memory()['bebidas'])})
            if path == '/api/catalog':
                return respond(200, app.read_memory())
            files = {'/': ('index.html', 'text/html; charset=utf-8'),
                     '/style.css': ('style.css', 'text/css; charset=utf-8'),
                     '/app.js': ('app.js', 'text/javascript; charset=utf-8')}
            if path not in files:
                return respond(404, {'error': 'Não encontrado'})
            name, kind = files[path]
            body = (app.ROOT / 'static' / name).read_bytes()
            if path == '/' and ephemeral():
                body = body.replace(b'<main>', ('<main><p role="note">' + NOTICE + '</p>').encode())
            return respond(200, body, kind)
        if method != 'POST':
            return respond(405, {'error': 'Método não permitido'})
        if path != '/api/chat':
            return respond(404, {'error': 'Não encontrado'})
        public_url = os.environ.get('BARIA_PUBLIC_URL') or os.environ.get('RENDER_EXTERNAL_URL')
        expected = (public_url or (environ.get('wsgi.url_scheme', 'http') + '://' + environ.get('HTTP_HOST', ''))).rstrip('/')
        origin = environ.get('HTTP_ORIGIN')
        if origin and origin != expected:
            return respond(403, {'error': 'Origem não permitida'})
        if not environ.get('CONTENT_TYPE', '').lower().startswith('application/json'):
            return respond(415, {'error': 'Envie JSON'})
        size = int(environ.get('CONTENT_LENGTH') or 0)
        if not 0 < size <= 12000:
            return respond(413, {'error': 'Mensagem muito grande ou vazia'})
        data = json.loads(environ['wsgi.input'].read(size))
        if not isinstance(data, dict):
            raise ValueError()
        text, prefs, action = data.get('message', ''), data.get('preferences', {}), data.get('action', 'chat')
        if not isinstance(text, str) or len(text) > 2000 or not isinstance(prefs, dict) or action not in ('chat', 'reset', 'finish', 'feedback'):
            raise ValueError()
        cookie = SimpleCookie(environ.get('HTTP_COOKIE', ''))
        sid = cookie['baria'].value if 'baria' in cookie else ''
        with app.LOCK:
            now = time.monotonic()
            for old, state in list(app.SESSIONS.items()):
                if now - state.get('_seen', 0) > SESSION_TTL:
                    del app.SESSIONS[old]
            if sid not in app.SESSIONS:
                sid = secrets.token_urlsafe(24)
                if len(app.SESSIONS) >= 1000:
                    app.SESSIONS.pop(next(iter(app.SESSIONS)))
                app.SESSIONS[sid] = {}
            state = app.SESSIONS[sid]
            # Limite básico por sessão; proteção de tráfego por IP cabe ao proxy.
            requests = [t for t in state.get('_requests', []) if now - t < 60]
            if len(requests) >= 30:
                return respond(429, {'error': 'Aguarde um minuto antes de enviar mais mensagens.'}, sid=sid)
            requests.append(now)
            result = app.reply(state, text, prefs, action)
            state.update(_seen=now, _requests=requests)
            if ephemeral() and ('salva na memória JSON' in result['message'] or result.get('adding') or action == 'feedback'):
                result['message'] += '\n\n' + NOTICE
        return respond(200, result, sid=sid)
    except (ValueError, TypeError, UnicodeError, CookieError):
        return respond(400, {'error': 'Dados inválidos'})
    except OSError:
        return respond(503, {'error': 'Memória indisponível. Tente novamente mais tarde.'})
