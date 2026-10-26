"""LZ77/LZSS sliding-window compression.

The input is scanned with a dictionary (window) of previously seen bytes and
a look-ahead of upcoming bytes.  The encoder either emits a literal byte or
a back-reference ``(distance, length)`` into the window.  A 3-byte hash
chain bounds the search.

Bit stream:
* 0 + 8 data bits                       -> literal
* 1 + 12 bits (distance-1) + 8 bits (length-3) -> match
The original length is stored in the header, so no end marker is needed.
"""

from .bits import BitWriter, BitReader

WINDOW_BITS = 12
WINDOW = 1 << WINDOW_BITS          # 4096
MIN_MATCH = 3
MAX_MATCH = MIN_MATCH + 255        # 258 (length-3 fits in 8 bits)
CHAIN_LIMIT = 128


def _hash3(data, i):
    return (data[i] << 16) | (data[i + 1] << 8) | data[i + 2]


def _best_match(data, i, candidates):
    end = len(data)
    best_len = 0
    best_dist = 0
    checked = 0
    for pos in reversed(candidates):
        if pos < i - WINDOW or pos >= i:
            break
        checked += 1
        if checked > CHAIN_LIMIT:
            break
        # quick hash match already implied; verify and extend
        max_len = min(MAX_MATCH, end - i)
        k = 0
        while k < max_len and data[pos + k] == data[i + k]:
            k += 1
        if k > best_len:
            best_len = k
            best_dist = i - pos
            if k == max_len:
                break
    return best_dist, best_len


def _tokens(data, record_steps=False):
    """Produce the literal/match token list."""
    n = len(data)
    table = {}
    tokens = []
    i = 0
    while i < n:
        if i + 2 < n:
            h = _hash3(data, i)
            cands = table.get(h)
            if cands:
                dist, length = _best_match(data, i, cands)
                if length >= MIN_MATCH:
                    tokens.append(("match", dist, length))
                    # insert all positions the match covers
                    for k in range(length):
                        if i + k + 2 < n:
                            hh = _hash3(data, i + k)
                            table.setdefault(hh, []).append(i + k)
                    i += length
                    continue
            table.setdefault(h, []).append(i)
        tokens.append(("lit", data[i]))
        i += 1
    return tokens


def encode(data, record_steps=False):
    tokens = _tokens(data, record_steps)
    out = bytearray()
    out += len(data).to_bytes(4, "big")
    w = BitWriter()
    for tok in tokens:
        if tok[0] == "lit":
            w.write_bit(0)
            w.write_bits(tok[1], 8)
        else:
            _, dist, length = tok
            w.write_bit(1)
            w.write_bits(dist - 1, WINDOW_BITS)
            w.write_bits(length - MIN_MATCH, 8)
    out += w.get_bytes()
    return bytes(out), tokens


def decode(buf):
    if len(buf) < 4:
        raise ValueError("truncated LZSS header")
    total = int.from_bytes(buf[:4], "big")
    r = BitReader(buf[4:])
    out = bytearray()
    while len(out) < total:
        flag = r.read_bit()
        if flag == 0:
            out.append(r.read_bits(8))
        else:
            dist = r.read_bits(WINDOW_BITS) + 1
            length = r.read_bits(8) + MIN_MATCH
            start = len(out) - dist
            if start < 0:
                raise ValueError("LZSS match before start")
            for k in range(length):
                out.append(out[start + k])
    return bytes(out)


def step_frames(data, limit=200):
    """Human-readable emission steps for the visualiser (capped)."""
    tokens = _tokens(data)
    frames = []
    pos = 0
    for tok in tokens:
        if len(frames) >= limit:
            break
        if tok[0] == "lit":
            frames.append({"pos": pos, "kind": "lit", "byte": tok[1],
                           "window_start": max(0, pos - WINDOW)})
            pos += 1
        else:
            _, dist, length = tok
            frames.append({"pos": pos, "kind": "match", "distance": dist,
                           "length": length, "from": pos - dist,
                           "window_start": max(0, pos - WINDOW)})
            pos += length
    return {"tokens": frames, "total_tokens": len(tokens),
            "window": WINDOW, "min_match": MIN_MATCH,
            "max_match": MAX_MATCH, "truncated": len(tokens) > limit}
