"""Servidor WSGI de implantação. Um processo: memória JSON e sessões compartilhadas."""
import app
import config
from web import application

if __name__ == '__main__':
    from waitress import serve
    app.initialize_storage()
    host, port = config.server_address()
    serve(application, host=host, port=port, threads=config.SERVER_THREADS,
          max_request_body_size=config.MAX_BODY_BYTES,
          max_request_header_size=config.MAX_HEADER_BYTES,
          channel_timeout=config.CHANNEL_TIMEOUT,
          connection_limit=config.CONNECTION_LIMIT)
