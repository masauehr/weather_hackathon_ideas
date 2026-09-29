"""ID-15 デモ用ローカルサーバー。

降水ナウキャストは「今から60分先まで」しか意味を持たないデータのため、GitHub Pagesのような
静的常時公開はできない（都度サーバー側で最新データを取りに行く必要がある）。
また対象JSONにはCORSヘッダーが無く、ブラウザから直接 fetch すると失敗するため、
本サーバーが気象庁への取得を代行し、結果だけをブラウザに返す（127.0.0.1限定）。

使い方: python server.py [port]  → http://127.0.0.1:8793/
出典: 気象庁ホームページ（高解像度降水ナウキャスト）
"""
import json
import sys
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

import fetch_nowcast as fn
import route as R

WEB_DIR = Path(__file__).parent / "webapp"
DEFAULT_PORT = 8793


def _json_default(o):
    if isinstance(o, datetime):
        return o.isoformat()
    raise TypeError


class Handler(BaseHTTPRequestHandler):
    def _host_ok(self):
        """DNSリバインディング対策: Hostヘッダーが自分自身(127.0.0.1:port)のときだけ受け付ける。"""
        port = self.server.server_port
        return (self.headers.get("Host") or "") in (f"127.0.0.1:{port}", f"localhost:{port}")

    def _send_json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False, default=_json_default).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if not self._host_ok():
            return self._send_json({"error": "forbidden host"}, 403)
        url = urlparse(self.path)
        if url.path == "/api/frames":
            return self._api_frames()
        if url.path == "/api/route":
            return self._api_route(parse_qs(url.query))
        return self._static(url.path)

    def _api_frames(self):
        try:
            base, vts = fn.current_forecast()
            self._send_json({"base": base, "validtimes": vts})
        except Exception as e:  # noqa: BLE001
            self._send_json({"error": str(e)}, 502)

    def _api_route(self, q):
        try:
            start = (float(q["start_lat"][0]), float(q["start_lon"][0]))
            end = (float(q["end_lat"][0]), float(q["end_lon"][0]))
            mode = q.get("mode", ["walk"])[0]
        except (KeyError, ValueError):
            return self._send_json({"error": "start_lat/start_lon/end_lat/end_lon が必要"}, 400)
        speed = R.WALK_MPS if mode == "walk" else R.BIKE_MPS
        try:
            result = R.recommend(start, end, speed)
            self._send_json(result)
        except Exception as e:  # noqa: BLE001
            self._send_json({"error": str(e)}, 502)

    def _static(self, path):
        rel = "index.html" if path in ("", "/") else path.lstrip("/")
        target = (WEB_DIR / rel).resolve()
        if WEB_DIR.resolve() not in target.parents or not target.is_file():
            return self._send(404, b"Not Found", "text/plain; charset=utf-8")
        ctype = "text/html; charset=utf-8"
        if target.suffix == ".js":
            ctype = "application/javascript; charset=utf-8"
        elif target.suffix == ".css":
            ctype = "text/css; charset=utf-8"
        self._send(200, target.read_bytes(), ctype)

    def _send(self, status, body, ctype):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        sys.stderr.write(f"{self.command} {urlparse(self.path).path}\n")


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PORT
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"http://127.0.0.1:{port}/")
    server.serve_forever()


if __name__ == "__main__":
    main()
