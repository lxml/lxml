"""
Simple HTTP request dumper for tests.
"""

import sys
from contextlib import contextmanager

try:
    import urlparse
except ImportError:
    # Python 3
    import urllib.parse as urlparse


@contextmanager
def webserver(app, port=0, host=None):
    """Context manager entry point for the 'with' statement.

    Pass 0 as port number to dynamically allocate a free port.

    Usage:

    with webserver(wsgi_app_function, 8080) as host_url:
        do_ws_calls(host_url)
    """
    server = build_web_server(app, port, host or '127.0.0.1')
    host, port = server.socket.getsockname()

    import threading
    thread = threading.Thread(target=server.serve_forever,
                              kwargs={'poll_interval': 0.5})
    thread.setDaemon(True)
    thread.start()
    try:
        yield 'http://%s:%s/' % (host, port)  # yield control to 'with' body
    finally:
        server.shutdown()
        server.server_close()
    thread.join(timeout=1)


try:
    from SocketServer import ThreadingMixIn
except ImportError:
    # Python 3
    from socketserver import ThreadingMixIn

import wsgiref.simple_server as wsgiserver
class WebServer(wsgiserver.WSGIServer, ThreadingMixIn):
    """A web server that starts a new thread for each request.
    """


class _RequestHandler(wsgiserver.WSGIRequestHandler):
    def get_stderr(self):
        # don't write to stderr
        return sys.stdout

    def log_message(self, format, *args):
        # message = "wsmock(%s) %s" % (self.address_string(), format % args)
        pass  # don't log messages


def build_web_server(app, port, host=None):
    server = wsgiserver.make_server(
        host or '', port, app,
        server_class=WebServer,
        handler_class=_RequestHandler)
    return server


class HTTPRequestCollector(object):
    def __init__(self, response_data, response_code=200, headers=()):
        self.requests = []
        self.response_code = response_code
        self.response_data = response_data
        self.headers = list(headers or ())

    def __call__(self, environ, start_response):
        self.requests.append((
            environ.get('PATH_INFO'),
            urlparse.parse_qsl(environ.get('QUERY_STRING'))))
        start_response('%s OK' % self.response_code, self.headers)
        return [self.response_data]
