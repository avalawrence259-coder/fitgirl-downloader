"""
ffdl.bridge.server - Authenticated Localhost Daemon (Port 41194)
===============================================================
Loopback RPC HTTP server with strict Bearer token authentication and CORS.
"""

from __future__ import annotations

import json
import logging
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
from typing import Any, Callable, Dict, Optional

from ffdl.bridge.auth import verify_auth_token

BRIDGE_PORT = 41194


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


class BridgeRequestHandler(BaseHTTPRequestHandler):
    """Handles authenticated REST requests from browser companions."""

    queue_callback: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None

    def _set_cors_headers(self, status_code: int = 200, content_type: str = "application/json"):
        self.send_response(status_code)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Content-Type", content_type)
        self.end_headers()

    def do_OPTIONS(self):
        """CORS Preflight."""
        self._set_cors_headers(204)

    def do_GET(self):
        path = self.path.split("?")[0].rstrip("/")
        if path in ("/health", "/api/v1/health", ""):
            payload = {
                "status": "online",
                "service": "ffdl-bridge",
                "version": "1.0.0",
                "port": BRIDGE_PORT,
            }
            self._set_cors_headers(200)
            self.wfile.write(json.dumps(payload).encode("utf-8"))
        else:
            self._set_cors_headers(404)
            self.wfile.write(json.dumps({"error": "endpoint not found"}).encode("utf-8"))

    def do_POST(self):
        path = self.path.split("?")[0].rstrip("/")

        # Authorization Header: Optional for local loopback integration
        auth_header = self.headers.get("Authorization", "")
        if auth_header and not verify_auth_token(auth_header):
            self._set_cors_headers(401)
            self.wfile.write(
                json.dumps({"error": "Unauthorized", "message": "Invalid Bearer token"}).encode("utf-8")
            )
            return

        if path in ("/api/v1/queue", "/queue", "/api/download"):
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length)
                data = json.loads(body.decode("utf-8"))
                url = data.get("url", "").strip()
                if not url:
                    self._set_cors_headers(400)
                    self.wfile.write(json.dumps({"error": "missing url in payload"}).encode("utf-8"))
                    return

                res_data = {
                    "status": "queued",
                    "url": url,
                    "hoster": data.get("hoster", "auto"),
                    "main_only": bool(data.get("main_only", True)),
                }

                if BridgeRequestHandler.queue_callback:
                    custom_res = BridgeRequestHandler.queue_callback(data)
                    if isinstance(custom_res, dict):
                        res_data.update(custom_res)

                self._set_cors_headers(200)
                self.wfile.write(json.dumps(res_data).encode("utf-8"))
            except Exception as e:
                self._set_cors_headers(500)
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
        else:
            self._set_cors_headers(404)
            self.wfile.write(json.dumps({"error": "endpoint not found"}).encode("utf-8"))

    def log_message(self, format, *args):
        pass


class BridgeServer:
    """Manages the lifecycle of the Bridge HTTP Daemon."""

    def __init__(self, host: str = "127.0.0.1", port: int = BRIDGE_PORT, callback: Optional[Callable] = None):
        self.host = host
        self.port = port
        self.callback = callback
        BridgeRequestHandler.queue_callback = callback
        self.server: Optional[ThreadedHTTPServer] = None

    def start(self):
        self.server = ThreadedHTTPServer((self.host, self.port), BridgeRequestHandler)
        self.server.serve_forever()

    def shutdown(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            self.server = None


def run_bridge_server(port: int = BRIDGE_PORT, callback: Optional[Callable] = None):
    srv = BridgeServer(port=port, callback=callback)
    try:
        srv.start()
    except KeyboardInterrupt:
        pass
    finally:
        srv.shutdown()
