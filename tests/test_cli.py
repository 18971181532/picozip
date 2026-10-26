import json
import os
import sys
import tempfile
import unittest
from io import StringIO

from picozip.cli import main

SAMPLE = b"the quick brown fox " * 120


class TestCLI(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.src = os.path.join(self.tmp, "in.txt")
        with open(self.src, "wb") as fh:
            fh.write(SAMPLE)

    def cli(self, *args):
        old = sys.stdout
        sys.stdout = StringIO()
        try:
            rc = main(list(args))
            return rc, sys.stdout.getvalue()
        finally:
            sys.stdout = old

    def test_compress_decompress_default(self):
        pz = os.path.join(self.tmp, "in.txt.pz")
        self.assertEqual(self.cli("compress", self.src, "-a", "hybrid")[0], 0)
        self.assertTrue(os.path.exists(pz))
        out = os.path.join(self.tmp, "restored.txt")
        self.assertEqual(self.cli("decompress", pz, "-o", out)[0], 0)
        with open(out, "rb") as fh:
            self.assertEqual(fh.read(), SAMPLE)

    def test_each_codec(self):
        for algo in ("rle", "huffman", "lzss", "lzw", "hybrid"):
            pz = os.path.join(self.tmp, algo + ".pz")
            out = os.path.join(self.tmp, algo + ".out")
            self.cli("compress", self.src, "-a", algo, "-o", pz)
            self.cli("decompress", pz, "-o", out)
            with open(out, "rb") as fh:
                self.assertEqual(fh.read(), SAMPLE, algo)

    def test_inspect_json(self):
        pz = os.path.join(self.tmp, "in.txt.pz")
        self.cli("compress", self.src, "-a", "lzss", "-o", pz)
        rc, out = self.cli("inspect", pz, "--json")
        info = json.loads(out)
        self.assertEqual(info["codec"], "lzss")
        self.assertEqual(info["original_size"], len(SAMPLE))

    def test_entropy(self):
        rc, out = self.cli("entropy", self.src)
        self.assertIn("entropy", out)

    def test_codecs_list(self):
        rc, out = self.cli("codecs")
        self.assertIn("hybrid", out)

    def test_bench_json(self):
        rc, out = self.cli("bench", "--json")
        payload = json.loads(out)
        self.assertIn("samples", payload)


if __name__ == "__main__":
    unittest.main()

