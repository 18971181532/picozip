import os
import unittest

from picozip import lzss


class TestLZSS(unittest.TestCase):
    def roundtrip(self, data):
        encoded, tokens = lzss.encode(data)
        self.assertEqual(lzss.decode(encoded), data, "roundtrip failed")

    def test_empty(self):
        self.roundtrip(b"")

    def test_short(self):
        self.roundtrip(b"abc")

    def test_overlapping_runs(self):
        self.roundtrip(b"a" * 2000)
        self.roundtrip(b"ab" * 1000)

    def test_repetitive_phrase(self):
        self.roundtrip(b"the quick brown fox " * 400)

    def test_beyond_window(self):
        # repeats separated by more than one 4096-byte window
        self.roundtrip(b"xyz" * 5000)

    def test_random(self):
        self.roundtrip(os.urandom(4000))

    def test_match_tokens_appear(self):
        _, tokens = lzss.encode(b"ABCABCABC" * 50)
        self.assertTrue(any(t[0] == "match" for t in tokens))

    def test_token_consistency(self):
        data = b"abcabcabc" * 30
        _, tokens = lzss.encode(data)
        pos = 0
        for token in tokens:
            if token[0] == "lit":
                pos += 1
            else:
                pos += token[2]
        self.assertEqual(pos, len(data))

    def test_frames(self):
        frames = lzss.step_frames(b"abcabcabc")
        self.assertTrue(frames["tokens"])
        self.assertGreater(frames["total_tokens"], 0)


if __name__ == "__main__":
    unittest.main()
