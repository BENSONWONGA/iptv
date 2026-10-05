# -*- coding: utf-8 -*-
"""本地预览服务器：静态 UI + API 反向代理（解决跨域）"""
import http.server
import socketserver
import urllib.request
import urllib.error
import os
import sys

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 3333
UPSTREAM = os.environ.get("ERP_BASE", "http://220.162.99.166:88")
UI_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui")


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=UI_DIR, **kw)

    def log_message(self, fmt, *args):
        sys.stderr.write("[%s] %s\n" % (self.address_string(), fmt % args))

    # ---------- SPA 路由 ----------
    def _spa_fallback(self):
        if self.path.startswith("/api/"):
            return False
        if self.path == "/":
            return True
        rel = self.path.split("?")[0].lstrip("/")
        fp = os.path.normpath(os.path.join(UI_DIR, rel))
        return not os.path.isfile(fp)

    def do_GET(self):
        if self.path.startswith("/api/"):
            return self.proxy("GET")
        if self._spa_fallback():
            self.path = "/index.html"
        super().do_GET()

    def do_HEAD(self):
        if self.path.startswith("/api/"):
            return self.proxy("HEAD")
        if self._spa_fallback():
            self.path = "/index.html"
        super().do_HEAD()

    def do_POST(self):
        if self.path.startswith("/api/"):
            return self.proxy("POST")
        self.send_error(404)

    def do_PUT(self):
        if self.path.startswith("/api/"):
            return self.proxy("PUT")
        self.send_error(404)

    def do_DELETE(self):
        if self.path.startswith("/api/"):
            return self.proxy("DELETE")
        self.send_error(404)

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type, Accept")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")

    # ---------- 代理 ----------
    def proxy(self, method):
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else None
        url = UPSTREAM + self.path  # /api/xxx 原样转发

        req = urllib.request.Request(url, data=body, method=method)
        for h in ("Authorization", "Content-Type", "Accept"):
            if self.headers.get(h):
                req.add_header(h, self.headers[h])

        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = resp.read()
                self.send_response(resp.status)
                ctype = resp.headers.get("Content-Type", "application/json")
                self.send_header("Content-Type", ctype)
                self._cors()
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                if method != "HEAD":
                    self.wfile.write(data)
        except urllib.error.HTTPError as e:
            data = e.read()
            self.send_response(e.code)
            self.send_header("Content-Type", e.headers.get("Content-Type", "application/json"))
            self._cors()
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            if method != "HEAD":
                self.wfile.write(data)
        except Exception as e:
            msg = ('{"error": "proxy: %s"}' % str(e)[:200]).encode()
            self.send_response(502)
            self.send_header("Content-Type", "application/json")
            self._cors()
            self.send_header("Content-Length", str(len(msg)))
            self.end_headers()
            self.wfile.write(msg)


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True


if __name__ == "__main__":
    with Server(("0.0.0.0", PORT), Handler) as httpd:
        print(f"UI 预览服务已启动: http://0.0.0.0:{PORT}  (代理 {UPSTREAM} , 静态目录 {UI_DIR})")
        httpd.serve_forever()
