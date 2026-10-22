"""Adaptador WSGI para a mesma lógica usada pelo servidor local."""
import json
import secrets
import time
from http import HTTPStatus
from http.cookies import CookieError, SimpleCookie

import config
from engine.catalog import KnowledgeError

SESSION_TTL = config.SESSION_TTL
NOTICE = ('Demonstração: conversas são temporárias; curiosidades e feedback podem ser '
          'apagados quando o servidor reiniciar. Não envie dados pessoais.')

def ephemeral():
    return config.ephemeral()

def application(environ, start_response, runtime=None):
    if runtime is None:
        import app as runtime

    method = environ.get('REQUEST_METHOD', 'GET')
    path = environ.get('PATH_INFO', '/')

    def respond(status, data, kind='application/json; charset=utf-8', sid=None):
        body = (
            json.dumps(data, ensure_ascii=False).encode()
            if isinstance(data, (dict, list)) else data
        )
        policy = (
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "img-src 'self' data:; connect-src 'self'; base-uri 'none'; "
            "frame-ancestors 'none'; form-action 'self'"
        )
        headers = [
            ('Content-Type', kind),
            ('Content-Length', str(len(body))),
            ('X-Content-Type-Options', 'nosniff'),
            ('Cache-Control', 'no-store'),
            ('Referrer-Policy', 'same-origin'),
            ('X-Frame-Options', 'DENY'),
            ('Content-Security-Policy', policy),
        ]
        if sid:
            secure = '; Secure' if config.secure_cookie() else ''
            cookie = f'baria={sid}; HttpOnly; SameSite=Strict; Path=/'
            headers.append(('Set-Cookie', cookie + f'; Max-Age={SESSION_TTL}{secure}'))
        start_response(f'{status} {HTTPStatus(status).phrase}', headers)
        return [b'' if method == 'HEAD' else body]

    try:
        if method in ('GET', 'HEAD'):
            if path == '/healthz':
                return respond(200, {'status': 'ok', 'drinks': len(runtime.read_memory()['bebidas'])})
            if path == '/api/catalog':
                return respond(200, runtime.read_memory())
            files = config.STATIC_FILES
            if path not in files:
                return respond(404, {'error': 'Não encontrado'})
            name, kind = files[path]
            body = (runtime.ROOT / 'static' / name).read_bytes()
            if path == '/' and ephemeral():
                body = body.replace(b'<main>', ('<main><p role="note">' + NOTICE + '</p>').encode())
            return respond(200, body, kind)
        if method != 'POST':
            return respond(405, {'error': 'Método não permitido'})
        if path != '/api/chat':
            return respond(404, {'error': 'Não encontrado'})
        expected = config.public_origin(environ)
        origin = environ.get('HTTP_ORIGIN')
        if origin and origin != expected:
            return respond(403, {'error': 'Origem não permitida'})
        media_type = environ.get('CONTENT_TYPE', '').split(';', 1)[0].strip().lower()
        if media_type != 'application/json':
            return respond(415, {'error': 'Envie JSON'})
        size = int(environ.get('CONTENT_LENGTH') or 0)
        if not 0 < size <= config.MAX_BODY_BYTES:
            return respond(413, {'error': 'Mensagem muito grande ou vazia'})
        data = json.loads(environ['wsgi.input'].read(size))
        if not isinstance(data, dict):
            raise ValueError()
        text = data.get('message', '')
        prefs = data.get('preferences', {})
        action = data.get('action', 'chat')
        if (
            not isinstance(text, str)
            or len(text) > config.MAX_MESSAGE_CHARS
            or not isinstance(prefs, dict)
            or action not in config.ACTIONS
        ):
            raise ValueError('Estrutura de mensagem inválida.')
        cookie = SimpleCookie(environ.get('HTTP_COOKIE', ''))
        sid = cookie['baria'].value if 'baria' in cookie else ''
        with runtime.LOCK:
            now = time.monotonic()
            for old, state in list(runtime.SESSIONS.items()):
                if now - state.get('_seen', 0) > SESSION_TTL:
                    del runtime.SESSIONS[old]
            if sid not in runtime.SESSIONS:
                sid = secrets.token_urlsafe(24)
                if len(runtime.SESSIONS) >= config.MAX_SESSIONS:
                    runtime.SESSIONS.pop(next(iter(runtime.SESSIONS)))
                runtime.SESSIONS[sid] = {}
            state = runtime.SESSIONS[sid]
            # Limite básico por sessão; proteção de tráfego por IP cabe ao proxy.
            requests = [t for t in state.get('_requests', []) if now - t < config.RATE_WINDOW]
            if len(requests) >= config.RATE_LIMIT:
                return respond(429, {'error': 'Aguarde um minuto antes de enviar mais mensagens.'}, sid=sid)
            requests.append(now)
            result = runtime.reply(state, text, prefs, action)
            state.update(_seen=now, _requests=requests)
            contribution = 'salva na memória JSON' in result['message']
            if ephemeral() and (contribution or result.get('adding') or action == 'feedback'):
                result['message'] += '\n\n' + NOTICE
        return respond(200, result, sid=sid)
    except KnowledgeError:
        return respond(503, {'error': 'Catálogo ou regras inválidos. Avise o responsável pelo serviço.'})
    except (ValueError, TypeError, UnicodeError, CookieError):
        return respond(400, {'error': 'Dados inválidos'})
    except OSError:
        return respond(503, {'error': 'Memória indisponível. Tente novamente mais tarde.'})
