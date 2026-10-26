import math
import unittest

from picozip import entropy


class TestEntropy(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(entropy.entropy_bits_per_byte(b""), 0.0)
        self.assertEqual(entropy.entropy_bits(b""), 0.0)

    def test_single_symbol(self):
        self.assertAlmostEqual(entropy.entropy_bits_per_byte(b"aaaaa"), 0.0)

    def test_uniform_two_symbols(self):
        self.assertAlmostEqual(entropy.entropy_bits_per_byte(b"ababab"), 1.0)

    def test_uniform_all_bytes(self):
        data = bytes(range(256))
        self.assertAlmostEqual(entropy.entropy_bits_per_byte(data), 8.0)

    def test_frequencies_count(self):
        freqs = entropy.frequencies(b"aaab")
        self.assertEqual(freqs[ord("a")], 3)
        self.assertEqual(freqs[ord("b")], 1)
        self.assertEqual(sum(freqs), 4)

    def test_information_content(self):
        data = b"abab"
        self.assertAlmostEqual(entropy.entropy_bits(data), 4.0)

    def test_top_symbols(self):
        top = entropy.top_symbols(b"aaabc", 2)
        self.assertEqual(top[0]["byte"], ord("a"))
        self.assertEqual(top[0]["count"], 3)


if __name__ == "__main__":
    unittest.main()
