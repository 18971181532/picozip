"""Hybrid LZSS + Huffman ("DEFLATE-lite").

The LZSS token stream is entropy-coded: literal bytes and the control
symbols ``END`` (256) and ``MATCH`` (257) are encoded with a canonical
Huffman code, while match distance/length are written as fixed-width
fields (12 / 8 bits).  This is the same two-stage idea as DEFLATE
(LZ77 + Huffman), with a deliberately simple symbol layout so it fits in a
small, readable implementation while still beating either stage alone.
"""

from .bits import BitWriter, BitReader
from .varint import write_varint, read_varint
from . import lzss
from . import huffman as huff

NSYM = 258
END = 256
MATCH = 257
DIST_BITS = lzss.WINDOW_BITS
LEN_BITS = 8


def encode(data):
    tokens = lzss._tokens(data)
    freqs = [0] * NSYM
    for tok in tokens:
        if tok[0] == "lit":
            freqs[tok[1]] += 1
        else:
            freqs[MATCH] += 1
    freqs[END] += 1

    lengths = huff.code_lengths(freqs)
    codes = huff.canonical_codes(lengths)

    out = bytearray()
    out += len(data).to_bytes(4, "big")
    present = [s for s in range(NSYM) if lengths[s]]
    out += write_varint(len(present))
    for s in present:
        out += write_varint(s)
        out.append(lengths[s])
    w = BitWriter()
    for tok in tokens:
        if tok[0] == "lit":
            code, length = codes[tok[1]]
            w.write_bits(code, length)
        else:
            _, dist, mlen = tok
            code, length = codes[MATCH]
            w.write_bits(code, length)
            w.write_bits(dist - 1, DIST_BITS)
            w.write_bits(mlen - lzss.MIN_MATCH, LEN_BITS)
    code, length = codes[END]
    w.write_bits(code, length)
    out += w.get_bytes()
    return bytes(out)


def _lookup_table(lengths, codes):
    max_len = max(lengths)
    table = [None] * (1 << max_len)
    for sym, (code, length) in codes.items():
        pad = max_len - length
        base = code << pad
        for suffix in range(1 << pad):
            table[base | suffix] = (sym, length)
    return table, max_len


def decode(buf):
    if len(buf) < 4:
        raise ValueError("truncated hybrid header")
    total = int.from_bytes(buf[:4], "big")
    pos = 4
    count, pos = read_varint(buf, pos)
    lengths = [0] * NSYM
    for _ in range(count):
        sym, pos = read_varint(buf, pos)
        if pos >= len(buf):
            raise ValueError("truncated hybrid code table")
        lengths[sym] = buf[pos]
        pos += 1
    payload = buf[pos:]
    codes = huff.canonical_codes(lengths)
    table, max_len = _lookup_table(lengths, codes)

    r = BitReader(payload)
    out = bytearray()
    while len(out) < total:
        window = r.read_bits(max_len)
        entry = table[window]
        if entry is None:
            raise ValueError("invalid hybrid code")
        sym, length = entry
        r.rewind(max_len - length)
        if sym == END:
            break
        if sym == MATCH:
            dist = r.read_bits(DIST_BITS) + 1
            mlen = r.read_bits(LEN_BITS) + lzss.MIN_MATCH
            start = len(out) - dist
            if start < 0:
                raise ValueError("hybrid match before start")
            for k in range(mlen):
                out.append(out[start + k])
        else:
            out.append(sym)
    return bytes(out)
