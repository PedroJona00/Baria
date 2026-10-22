"""Configurações compartilhadas pela execução local e pela hospedagem."""
import os
from pathlib import Path

MAX_BODY_BYTES = 12_000
MAX_MESSAGE_CHARS = 2_000
MAX_PREFERENCE_CHARS = 300
SESSION_TTL = 3_600
MAX_SESSIONS = 1_000
RATE_WINDOW = 60
RATE_LIMIT = 30
SERVER_THREADS = 4
CHANNEL_TIMEOUT = 30
CONNECTION_LIMIT = 100
MAX_HEADER_BYTES = 16_384
ACTIONS = ('chat', 'reset', 'finish', 'feedback')
FLAVORS = ('doce', 'citrico', 'amargo', 'frutado', 'cremoso', 'refrescante', 'quente')
STATIC_FILES = {
    '/': ('index.html', 'text/html; charset=utf-8'),
    '/style.css': ('style.css', 'text/css; charset=utf-8'),
    '/app.js': ('app.js', 'text/javascript; charset=utf-8'),
}


def data_directory(root):
    return Path(os.environ.get('BARIA_DATA_DIR', str(root / 'data')))


def server_address():
    port = int(os.environ.get('PORT', '8000'))
    if not 1 <= port <= 65535:
        raise ValueError('PORT precisa estar entre 1 e 65535.')
    return os.environ.get('HOST', '127.0.0.1'), port


def public_origin(environ):
    configured = os.environ.get('BARIA_PUBLIC_URL') or os.environ.get('RENDER_EXTERNAL_URL')
    return (configured or (environ.get('wsgi.url_scheme', 'http') + '://' + environ.get('HTTP_HOST', ''))).rstrip('/')


def secure_cookie():
    return os.environ.get('BARIA_SECURE_COOKIE') == '1'


def ephemeral():
    return os.environ.get('BARIA_STORAGE_MODE') == 'ephemeral'
