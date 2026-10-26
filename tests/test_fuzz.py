import random
import unittest

from picozip import codecs, rle, huffman, lzss, lzw, hybrid


def random_cases():
    rng = random.Random(20260926)
    cases = [
        bytes(rng.randrange(256) for _ in range(n))
        for n in (0, 1, 2, 50, 500, 5000)
    ]
    # binary: runs + sparse random
    blob = bytearray()
    for _ in range(60):
        blob += bytes([rng.randrange(256)]) * rng.randrange(1, 60)
    cases.append(bytes(blob))
    # small alphabet
    cases.append(bytes(rng.choice(b"abcde ") for _ in range(4000)))
    # period of prime length (resets mid phrase)
    pat = b"0123456789ABCDEF"
    cases.append(pat * 400)
    return cases


CODECS = {
    "rle": rle,
    "huffman": huffman,
    "lzss": lzss,
    "lzw": lzw,
    "hybrid": hybrid,
}


class TestFuzz(unittest.TestCase):
    def test_all_codecs_all_cases(self):
        for data in random_cases():
            for name, mod in CODECS.items():
                if name == "lzss":
                    encoded, _ = mod.encode(data)
                else:
                    encoded = mod.encode(data)
                decoded = mod.decode(encoded)
                self.assertEqual(decoded, data,
                                 f"{name} failed on {len(data)} bytes")


if __name__ == "__main__":
    unittest.main()
