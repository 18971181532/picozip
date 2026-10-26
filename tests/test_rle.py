import unittest

from picozip import rle


class TestRLE(unittest.TestCase):
    def roundtrip(self, data):
        encoded = rle.encode(data)
        self.assertEqual(rle.decode(encoded), data)

    def test_basic(self):
        self.roundtrip(b"aaabbbcccd")

    def test_empty(self):
        self.roundtrip(b"")

    def test_single(self):
        self.roundtrip(b"a")

    def test_long_runs(self):
        self.roundtrip(b"\x00" * 5000 + b"\xff" * 3000)

    def test_no_runs(self):
        self.roundtrip(b"abcdefghijklmnopqrstuvwxyz")

    def test_boundary_singletons(self):
        self.roundtrip(b"a" * 2 + b"b" * 2 + b"c" * 2)

    def test_runs_structure(self):
        runs = rle.runs(b"aaabb")
        self.assertEqual([(r["byte"], r["length"]) for r in runs],
                         [(97, 3), (98, 2)])


if __name__ == "__main__":
    unittest.main()
