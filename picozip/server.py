"""Local HTTP server for the PicoZip visual workbench.

A single JSON analysis endpoint computes every codec's result and the
per-algorithm animation frames (Huffman merges, LZSS sliding window, LZW
dictionary growth); the static web bundle renders them.  Bound to
127.0.0.1 and only touches the text posted in the request.
"""

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from . import __version__
from . import huffman, lzss, lzw, rle, bench, container
from .entropy import entropy_bits_per_byte, top_symbols

WEB_DIR = os.path.join(os.path.dirname(__file__), "web")

CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
}

MAX_TEXT = 200000
FRAME_LIMIT = 220


def analyze(text):
    data = text.encode("utf-8")[:MAX_TEXT]
    result = bench.bench_data(data)
    return {
        "original_text": text,
        "original_size": len(data),
        "entropy": {
            "bits_per_byte": round(entropy_bits_per_byte(data), 4),
            "ideal_bytes": round(entropy_bits_per_byte(data) * len(data) / 8, 1),
            "top": top_symbols(data, 16),
        },
        "codecs": result["rows"],
        "huffman": huffman.analyze(data),
        "lzss": lzss.step_frames(data, limit=FRAME_LIMIT),
        "lzw": lzw.step_frames(data, limit=FRAME_LIMIT),
        "rle": {"runs": rle.runs(data, limit=FRAME_LIMIT),
                "window": lzss.WINDOW},
    }


def roundtrip(text, algo):
    data = text.encode("utf-8")
    blob = container.pack(data, algo)
    return container.unpack(blob) == data


class Handler(BaseHTTPRequestHandler):
    server_version = f"PicoZip/{__version__}"

    def log_message(self, *args):
        pass

    def _json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _error(self, msg, status=400):
        self._json({"error": str(msg)}, status)

    def _read_body(self):
        length = int(self.headers.get("Content-Length", "0") or 0)
        if not length:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            return {}

    def do_GET(self):
        route = urlparse(self.path).path
        if route == "/api/health":
            return self._json({"status": "ok", "version": __version__})
        return self._static(route)

    def do_POST(self):
        route = urlparse(self.path).path
        payload = self._read_body()
        try:
            if route == "/api/analyze":
                return self._json(analyze(payload.get("text", "")))
            if route == "/api/bench":
                text = payload.get("text")
                if text:
                    return self._json(bench.bench_data(text.encode("utf-8")))
                return self._json({"samples": bench.bench_samples()})
            return self._error("unknown route", 404)
        except Exception as exc:
            return self._error(str(exc), 500)

    def _static(self, route):
        if route in ("", "/"):
            route = "/index.html"
        rel = route.lstrip("/")
        safe = os.path.normpath(os.path.join(WEB_DIR, rel))
        if not safe.startswith(os.path.abspath(WEB_DIR)) or \
                not os.path.isfile(safe):
            return self._error("not found", 404)
        with open(safe, "rb") as fh:
            body = fh.read()
        ext = os.path.splitext(safe)[1].lower()
        self.send_response(200)
        self.send_header("Content-Type",
                         CONTENT_TYPES.get(ext, "application/octet-stream"))
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def serve(host="127.0.0.1", port=8858):
    httpd = ThreadingHTTPServer((host, port), Handler)
    url = f"http://{host}:{port}/"
    print("PicoZip compression workbench")
    print(f"Dashboard: {url}  (Ctrl+C to stop)")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
    finally:
        httpd.server_close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="PicoZip workbench server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8858)
    args = parser.parse_args()
    serve(args.host, args.port)
