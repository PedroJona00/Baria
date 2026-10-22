"""Servidor WSGI de implantação. Um processo: memória JSON e sessões compartilhadas."""
import os
import app
from web import application

if __name__ == '__main__':
    from waitress import serve
    app.initialize_storage()
    serve(application, host=os.environ.get('HOST', '127.0.0.1'),
          port=int(os.environ.get('PORT', '8000')), threads=4,
          max_request_body_size=12000, max_request_header_size=16384,
          channel_timeout=30, connection_limit=100)
