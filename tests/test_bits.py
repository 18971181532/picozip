import unittest

from picozip.bits import BitWriter, BitReader


class TestBits(unittest.TestCase):
    def test_mixed_widths(self):
        w = BitWriter()
        vals = [(1, 1), (0, 1), (5, 3), (0, 4), (255, 8), (0, 1), (7, 3)]
        for value, width in vals:
            w.write_bits(value, width)
        r = BitReader(w.get_bytes())
        for value, width in vals:
            self.assertEqual(r.read_bits(width), value)

    def test_single_bit_stream(self):
        w = BitWriter()
        seq = [1, 0, 1, 1, 0, 0, 1, 0, 1, 1]
        for b in seq:
            w.write_bit(b)
        r = BitReader(w.get_bytes())
        self.assertEqual([r.read_bit() for _ in seq], seq)

    def test_rewind(self):
        w = BitWriter()
        w.write_bits(0b1101, 4)
        w.write_bits(0b101, 3)
        r = BitReader(w.get_bytes())
        self.assertEqual(r.read_bits(4), 0b1101)
        self.assertEqual(r.pos, 4)
        r.rewind(2)
        self.assertEqual(r.pos, 2)
        self.assertEqual(r.read_bits(3), 0b011)  # re-read bit2,3 + next

    def test_padding_bits_are_zero(self):
        w = BitWriter()
        w.write_bits(0b11, 2)
        r = BitReader(w.get_bytes())
        self.assertEqual(r.read_bits(8), 0b11000000)

    def test_bit_count(self):
        w = BitWriter()
        w.write_bits(0b1, 1)
        self.assertEqual(w.bit_count(), 1)
        w.write_bits(0b1, 1)
        self.assertEqual(w.bit_count(), 2)


if __name__ == "__main__":
    unittest.main()
