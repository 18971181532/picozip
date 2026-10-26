"""MSB-first bit-level I/O.

Compression codecs work in fractions of a byte.  ``BitWriter`` packs bits
most-significant-bit first into bytes, and ``BitReader`` unpacks them the
same way.  The final byte is zero-padded; codecs always know exactly how
many bits/symbols to decode, so trailing padding is ignored.
"""


class BitWriter:
    def __init__(self):
        self._out = bytearray()
        self._cur = 0
        self._nbits = 0

    def write_bit(self, bit):
        self._cur = (self._cur << 1) | (1 if bit else 0)
        self._nbits += 1
        if self._nbits == 8:
            self._out.append(self._cur)
            self._cur = 0
            self._nbits = 0

    def write_bits(self, value, width):
        """Write ``width`` bits of ``value``, most-significant bit first."""
        for i in range(width - 1, -1, -1):
            self.write_bit((value >> i) & 1)

    def get_bytes(self):
        out = bytearray(self._out)
        if self._nbits:
            out.append(self._cur << (8 - self._nbits))
        return bytes(out)

    def bit_count(self):
        return len(self._out) * 8 + self._nbits


class BitReader:
    """Reads MSB-first bits; position is a single integer bit offset."""

    def __init__(self, data):
        self._data = data
        self.pos = 0

    def read_bit(self):
        byte_idx = self.pos >> 3
        if byte_idx >= len(self._data):
            # Past the end we only see zero padding bits. Codecs stop based
            # on their own length/symbol counts, so a truncated stream shows
            # up as a bad lookup rather than an exception here.
            self.pos += 1
            return 0
        bit_idx = 7 - (self.pos & 7)
        self.pos += 1
        return (self._data[byte_idx] >> bit_idx) & 1

    def read_bits(self, width):
        value = 0
        for _ in range(width):
            value = (value << 1) | self.read_bit()
        return value

    def rewind(self, nbits):
        """Move the read position backwards by ``nbits``."""
        self.pos -= nbits

    def align(self):
        """Discard the padding bits of the current byte."""
        rem = self.pos & 7
        if rem:
            self.pos += 8 - rem
