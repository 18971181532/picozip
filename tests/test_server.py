import json
import threading
import unittest
import urllib.request
from http.server import ThreadingHTTPServer

from picozip.server import Handler


def _post(url, obj):
    data = json.dumps(obj).encode("utf-8")
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _get(url):
    with urllib.request.urlopen(url, timeout=30) as resp:
        return resp.status, resp.read()


class TestServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.port = cls.httpd.server_address[1]
        cls.thread = threading.Thread(target=cls.httpd.serve_forever,
                                     daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.port}"

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def test_health(self):
        status, body = _get(self.base + "/api/health")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["status"], "ok")

    def test_index(self):
        status, body = _get(self.base + "/")
        self.assertEqual(status, 200)
        self.assertIn(b"PicoZip", body)

    def test_analyze(self):
        r = _post(self.base + "/api/analyze",
                  {"text": "abracadabra " * 30})
        self.assertEqual(r["original_size"], len(b"abracadabra " * 30))
        self.assertIn("entropy", r)
        self.assertEqual(len(r["codecs"]), 5)
        self.assertTrue(all(row["roundtrip"] for row in r["codecs"]))
        self.assertIn("tree", r["huffman"])
        self.assertTrue(r["lzss"]["tokens"])
        self.assertTrue(r["lzw"]["frames"])

    def test_analyze_empty(self):
        r = _post(self.base + "/api/analyze", {"text": ""})
        self.assertEqual(r["original_size"], 0)

    def test_bench_samples(self):
        r = _post(self.base + "/api/bench", {})
        self.assertIn("samples", r)
        self.assertIn("text", r["samples"])

    def test_bench_text(self):
        r = _post(self.base + "/api/bench", {"text": "abc" * 100})
        self.assertEqual(len(r["rows"]), 5)

    def test_404(self):
        import urllib.error
        with self.assertRaises(urllib.error.HTTPError):
            _get(self.base + "/does-not-exist")


if __name__ == "__main__":
    unittest.main()
