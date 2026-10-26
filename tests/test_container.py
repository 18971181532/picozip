import unittest

from picozip import container, codecs
from picozip.container import IntegrityError


SAMPLE = b"the quick brown fox jumps over the lazy dog. " * 100


class TestContainer(unittest.TestCase):
    def test_all_codecs_roundtrip(self):
        for algo in codecs.ORDER:
            blob = container.pack(SAMPLE, algo)
            self.assertEqual(blob[:2], b"PZ")
            self.assertEqual(container.unpack(blob), SAMPLE)

    def test_empty(self):
        blob = container.pack(b"", "hybrid")
        self.assertEqual(container.unpack(blob), b"")

    def test_inspect(self):
        blob = container.pack(SAMPLE, "lzss")
        info = container.inspect(blob)
        self.assertEqual(info["codec"], "lzss")
        self.assertEqual(info["codec_id"], codecs.REGISTRY["lzss"]["id"])
        self.assertEqual(info["original_size"], len(SAMPLE))
        self.assertLess(info["ratio"], 1.0)

    def test_corrupt_payload_detected(self):
        blob = bytearray(container.pack(SAMPLE, "hybrid"))
        blob[30] ^= 0xFF  # flip a payload byte
        with self.assertRaises((IntegrityError, Exception)):
            container.unpack(bytes(blob))

    def test_bad_magic(self):
        with self.assertRaises(ValueError):
            container.inspect(b"XX" + b"\x00" * 30)

    def test_truncated(self):
        with self.assertRaises(ValueError):
            container.unpack(b"PZ\x01\x05")

    def test_unknown_codec(self):
        blob = bytearray(container.pack(SAMPLE, "rle"))
        blob[3] = 99
        with self.assertRaises(ValueError):
            container.unpack(bytes(blob))


if __name__ == "__main__":
    unittest.main()
