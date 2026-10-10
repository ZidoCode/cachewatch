#!/usr/bin/env python3
"""router v2 — one-domain reverse router built on http.server.

Ports: 80 and 7680. Routing per request (stdlib handles keep-alive):
  /cw/*  -> cachewatch (127.0.0.1:20130), prefix rewritten /cw -> /_cw
  /*     -> ttyd       (127.0.0.1:7681, runs with -b /term)
WebSocket upgrade requests are tunneled raw after the 101 response.
"""
import os
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

TTYD = ("127.0.0.1", 7681)
CACHEWATCH = ("127.0.0.1", 20130)
CW_PREFIX = "/cw"
PORTS = [int(p) for p in os.environ.get("RT_PORTS", "80,7680").split(",")]


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.0"  # force close per request — cloudflared-safe

    def log_message(self, fmt, *args):
        print(f"ACCESS {self.client_address[0]} {self.command} {self.path.split('?')[0]}", flush=True)

    def _route(self):
        path = self.path
        if path == CW_PREFIX or path.startswith(CW_PREFIX + "/") or path.startswith(CW_PREFIX + "?"):
            return CACHEWATCH, "/_cw" + path[len(CW_PREFIX):]
        if path.startswith("/v1") or path.startswith("/dashboard") or path.startswith("/login") or path.startswith("/callback") or path.startswith("/_next/") or path.startswith("/api/") or path in ("/favicon.ico", "/favicon.svg", "/manifest.webmanifest"):
            return CACHEWATCH, path
        return TTYD, path

    def _relay_ws(self, target, first_line, headers):
        """Raw TCP pipe for WebSocket upgrades (ttyd terminal)."""
        try:
            up = socket.create_connection(target, timeout=15)
            up.sendall((first_line + "\r\n" + headers + "\r\n\r\n").encode("latin-1"))
            self.close_connection = True
            self.connection.settimeout(None)
            up.settimeout(None)
            c = self.connection

            def pump(a, b):
                try:
                    while True:
                        d = a.recv(65536)
                        if not d:
                            break
                        b.sendall(d)
                except Exception:
                    pass
                finally:
                    try:
                        b.shutdown(socket.SHUT_WR)
                    except Exception:
                        pass

            t1 = threading.Thread(target=pump, args=(c, up), daemon=True)
            t2 = threading.Thread(target=pump, args=(up, c), daemon=True)
            t1.start(); t2.start(); t1.join(); t2.join()
        except Exception:
            pass

    def _forward(self):
        print(f"ACCESS {self.client_address[0]} {self.command} {self.path.split('?')[0]}", flush=True)
        target, upstream_path = self._route()
        first_line = f"{self.command} {upstream_path} {self.request_version}"
        headers = []
        for k, v in self.headers.items():
            if k.lower() == "host":
                headers.append(f"Host: {target[0]}:{target[1]}")
            else:
                headers.append(f"{k}: {v}")

        if (self.headers.get("Upgrade", "").lower() == "websocket"
                or "upgrade" in self.headers.get("Connection", "").lower()):
            return self._relay_ws(target, first_line, "\r\n".join(headers))

        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else b""

        try:
            up = socket.create_connection(target, timeout=30)
        except Exception:
            payload = b'{"error":{"message":"upstream unreachable"}}'
            self.send_response(502)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return

        try:
            req = first_line + "\r\n" + "\r\n".join(headers) + "\r\nConnection: close\r\n\r\n"
            up.sendall(req.encode("latin-1") + body)

            self.close_connection = True
            while True:
                chunk = up.recv(65536)
                if not chunk:
                    break
                self.wfile.write(chunk)
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception:
            pass
        finally:
            try:
                up.close()
            except Exception:
                pass

    def do_GET(self):
        self._forward()

    def do_POST(self):
        self._forward()

    def do_PUT(self):
        self._forward()

    def do_DELETE(self):
        self._forward()

    def do_PATCH(self):
        self._forward()

    def do_HEAD(self):
        self._forward()

    def do_OPTIONS(self):
        self._forward()


def serve(port: int) -> None:
    srv = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    srv.daemon_threads = True
    print(f"router v2 on 0.0.0.0:{port} -> ttyd{TTYD} | {CW_PREFIX}/* -> cachewatch{CACHEWATCH}", flush=True)
    srv.serve_forever()


def main():
    threads = [threading.Thread(target=serve, args=(p,), daemon=True) for p in PORTS]
    for t in threads:
        t.start()
    for t in threads:
        t.join()


if __name__ == "__main__":
    main()
