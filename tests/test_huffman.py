import unittest

from picozip import huffman


def codes_of(data):
    freqs = huffman.frequencies(data)
    lengths = huffman.code_lengths(freqs)
    raw = huffman.canonical_codes(lengths)
    # raw[s] = (code_int, length); turn into zero-padded binary strings
    return {s: format(pair[0], "0{}b".format(pair[1]))
            for s, pair in raw.items()}


class TestHuffman(unittest.TestCase):
    def roundtrip(self, data):
        self.assertEqual(huffman.decode(huffman.encode(data)), data)

    def test_basic(self):
        self.roundtrip(b"abracadabra")

    def test_empty(self):
        self.roundtrip(b"")

    def test_single_byte(self):
        self.roundtrip(b"aaaaaaa")

    def test_two_symbols(self):
        self.roundtrip(b"ab" * 500)

    def test_large_text(self):
        text = (b"the quick brown fox jumps over the lazy dog. " * 300)
        self.roundtrip(text)

    def test_codes_are_prefix_free(self):
        data = b"abracadabra the quick brown fox"
        codes = set(codes_of(data).values())
        for a in codes:
            for b in codes:
                if a != b:
                    self.assertFalse(a.startswith(b),
                                     f"{a} has prefix {b}")

    def test_canonical_ordering(self):
        # shorter codes come first; same length: smaller symbol lexicographically
        data = b"abracadabra"
        freqs = huffman.frequencies(data)
        lengths = huffman.code_lengths(freqs)
        codes = codes_of(data)
        # ordered by (length, symbol) canonical codes must be non-decreasing
        ordered = sorted(codes, key=lambda s: (lengths[s], s))
        vals = [int(codes[s], 2) for s in ordered]
        self.assertEqual(vals, sorted(vals))

    def test_single_symbol_length_one(self):
        freqs = huffman.frequencies(b"aaaa")
        lengths = huffman.code_lengths(freqs)
        present = [l for l in lengths if l]
        self.assertEqual(present, [1])

    def test_analyze(self):
        a = huffman.analyze(b"abracadabra")
        self.assertTrue(a["codes"])
        self.assertEqual(a["mean_length"] > 0, True)
        self.assertIn("tree", a)
        self.assertIn("merges", a)


if __name__ == "__main__":
    unittest.main()
