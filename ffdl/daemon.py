"""
ffdl.daemon - Micro HTTP Background Server for Browser Extension Integration
===========================================================================
Listens on localhost:45732 to receive download jobs directly from the browser extension
with CORS support and status reporting.
"""

from __future__ import annotations

import asyncio
import json
import logging
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Callable, Optional

DEFAULT_PORT = 45732


class ExtensionAPIHandler(BaseHTTPRequestHandler):
    """Handles REST requests from FFDL browser extensions."""

    job_callback: Optional[Callable] = None

    def _set_cors_headers(self, status_code: int = 200, content_type: str = "application/json"):
        self.send_response(status_code)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Content-Type", content_type)
        self.end_headers()

    def do_OPTIONS(self):
        self._set_cors_headers(204)

    def do_GET(self):
        path = self.path.split("?")[0]
        if path in ("/health", "/api/status", "/"):
            payload = {
                "status": "online",
                "app": "ffdl-accelerator",
                "version": "1.0.0",
                "port": DEFAULT_PORT,
            }
            self._set_cors_headers(200)
            self.wfile.write(json.dumps(payload).encode("utf-8"))
        else:
            self._set_cors_headers(404)
            self.wfile.write(json.dumps({"error": "not found"}).encode("utf-8"))

    def do_POST(self):
        path = self.path.split("?")[0]
        if path in ("/api/download", "/download"):
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length)
                data = json.loads(body.decode("utf-8"))
                url = data.get("url", "").strip()
                if not url:
                    self._set_cors_headers(400)
                    self.wfile.write(json.dumps({"error": "missing url"}).encode("utf-8"))
                    return

                if ExtensionAPIHandler.job_callback:
                    ExtensionAPIHandler.job_callback(data)

                self._set_cors_headers(200)
                self.wfile.write(json.dumps({
                    "status": "accepted",
                    "url": url,
                    "hoster": data.get("hoster", "auto"),
                    "main_only": bool(data.get("main_only", False)),
                }).encode("utf-8"))
            except Exception as e:
                self._set_cors_headers(500)
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
        else:
            self._set_cors_headers(404)
            self.wfile.write(json.dumps({"error": "endpoint not found"}).encode("utf-8"))

    def log_message(self, format, *args):
        # Suppress noisy standard HTTP access logging
        pass


def run_daemon_server(port: int = DEFAULT_PORT, callback: Optional[Callable] = None):
    """Starts synchronous HTTP server daemon listening for browser requests."""
    ExtensionAPIHandler.job_callback = callback
    server = HTTPServer(("127.0.0.1", port), ExtensionAPIHandler)
    print(f"\n⚡ FFDL Background Daemon listening on http://127.0.0.1:{port}")
    print("📡 Ready to receive download triggers from the FFDL Browser Extension...")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
