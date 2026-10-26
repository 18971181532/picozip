"""Run-length encoding.

Each maximal run is stored as ``varint(length) + byte``.  RLE is a trivial
baseline: it compresses run-heavy data very well and expands random data,
which makes the point that no single codec wins for every input.
"""

from .varint import write_varint, read_varint

MAX_RUN = (1 << 28) - 1


def encode(data):
    out = bytearray()
    i = 0
    n = len(data)
    while i < n:
        b = data[i]
        j = i + 1
        while j < n and data[j] == b and (j - i) < MAX_RUN:
            j += 1
        out += write_varint(j - i)
        out.append(b)
        i = j
    return bytes(out)


def decode(buf):
    out = bytearray()
    pos = 0
    while pos < len(buf):
        count, pos = read_varint(buf, pos)
        if pos >= len(buf):
            raise ValueError("truncated RLE block")
        b = buf[pos]
        pos += 1
        out.extend(bytes([b]) * count)
    return bytes(out)


def runs(data, limit=200):
    """Describe the maximal runs (for the visualiser)."""
    steps = []
    i = 0
    n = len(data)
    while i < n and len(steps) < limit:
        b = data[i]
        j = i + 1
        while j < n and data[j] == b:
            j += 1
        steps.append({"start": i, "end": j, "byte": b, "length": j - i})
        i = j
    return steps
