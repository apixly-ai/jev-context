"""Dependency-free, read-only loopback dashboard. No third-party assets or telemetry."""

import errno
import json
import secrets
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from .stats import report

DEFAULT_PORT = 8765


class DashboardHTTPServer(ThreadingHTTPServer):
    # Never share a port with another instance carrying a different access token.
    allow_reuse_port = False


class PortInUse(ValueError):
    pass


def page(data, live=False):
    template = Path(__file__).with_name("dashboard.html").read_text()
    payload = (
        json.dumps(data, ensure_ascii=False)
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
    )
    return template.replace("__DATA__", payload).replace("__LIVE__", "true" if live else "false")


def server(port=None, model=None, since=None, until=None):
    token = secrets.token_urlsafe(24)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            target = urlsplit(self.path)
            host = self.headers.get("Host", "")
            allowed = {
                f"127.0.0.1:{self.server.server_port}",
                f"localhost:{self.server.server_port}",
            }
            if host not in allowed or parse_qs(target.query).get("token") != [token]:
                self.send_error(403)
                return
            if target.path not in ("/", "/data"):
                self.send_error(404)
                return
            try:
                data = report(model, since, until)
                body = (
                    json.dumps(data, ensure_ascii=False)
                    if target.path == "/data"
                    else page(data, True)
                ).encode()
            except Exception:
                self.send_error(500, "Statistics unavailable")
                return
            self.send_response(200)
            self.send_header(
                "Content-Type",
                "application/json; charset=utf-8"
                if target.path == "/data"
                else "text/html; charset=utf-8",
            )
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'",
            )
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    requested = DEFAULT_PORT if port is None else port
    try:
        httpd = DashboardHTTPServer(("127.0.0.1", requested), Handler)
    except OSError as error:
        if error.errno != errno.EADDRINUSE:
            raise
        if port is not None:
            raise PortInUse from None
        httpd = DashboardHTTPServer(("127.0.0.1", 0), Handler)
    return httpd, f"http://127.0.0.1:{httpd.server_port}/?token={token}"


def serve(port=None, model=None, since=None, until=None):
    try:
        httpd, url = server(port, model, since, until)
    except PortInUse:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error_type": "PortInUse",
                    "port": port,
                    "message": f"Port {port} is already in use. Run jev-filter stats dashboard --port 0 to choose an available port.",
                }
            ),
            file=sys.stderr,
        )
        return 1
    print(json.dumps({"dashboard": url, "bind": "loopback", "read_only": True}), flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()

    return 0
