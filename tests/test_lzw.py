import os
import unittest

from picozip import lzw


class TestLZW(unittest.TestCase):
    def roundtrip(self, data):
        self.assertEqual(lzw.decode(lzw.encode(data)), data)

    def test_empty(self):
        self.roundtrip(b"")

    def test_single_byte(self):
        self.roundtrip(b"a")

    def test_simple_repetition(self):
        self.roundtrip(b"abababab")

    def test_text(self):
        self.roundtrip(b"the rain in spain falls mainly on the plain " * 100)

    def test_dict_reset(self):
        # more than 3838 newly learned phrases forces a CLEAR code
        data = (b"abcdefghijklmnopqrstuvwxyz0123456789" * 120)
        self.assertGreater(len(data), 4096)
        self.roundtrip(data)

    def test_random(self):
        self.roundtrip(os.urandom(5000))

    def test_kwkw(self):
        # classic decoder "KwKw" edge case
        self.roundtrip(b"ababababa" * 10)

    def test_frames(self):
        frames = lzw.step_frames(b"ababab")
        self.assertTrue(frames["frames"])
        self.assertEqual(frames["max_codes"], 4096)


if __name__ == "__main__":
    unittest.main()
