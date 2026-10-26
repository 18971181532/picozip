import os
import unittest

from picozip import hybrid


class TestHybrid(unittest.TestCase):
    def roundtrip(self, data):
        self.assertEqual(hybrid.decode(hybrid.encode(data)), data)

    def test_empty(self):
        self.roundtrip(b"")

    def test_single(self):
        self.roundtrip(b"a")

    def test_text(self):
        self.roundtrip(b"abracadabra " * 200)

    def test_source_code(self):
        with open(__file__, "rb") as fh:
            self.roundtrip(fh.read())

    def test_random(self):
        self.roundtrip(os.urandom(3000))

    def test_compresses_repetitive(self):
        data = b"abcdefgh" * 1000
        self.assertLess(len(hybrid.encode(data)), len(data))


if __name__ == "__main__":
    unittest.main()
