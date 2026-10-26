"""LZW (Lempel-Ziv-Welch) dictionary coding.

Fixed 12-bit codes (GIF-style) with a clear code.  The dictionary starts
with the 256 single bytes; when it fills up (4096 entries) a clear code is
emitted and both encoder and decoder rebuild it from scratch.

* 0..255 : literal bytes
* 256    : CLEAR (reset dictionary)
* 257    : END (end of stream)
"""

from .bits import BitWriter, BitReader

CODE_BITS = 12
MAX_CODES = 1 << CODE_BITS      # 4096
CLEAR = 256
END = 257
FIRST_CODE = 258


def _new_table():
    return {bytes([i]): i for i in range(256)}


def encode(data):
    w = BitWriter()
    table = _new_table()
    next_code = FIRST_CODE
    w.write_bits(CLEAR, CODE_BITS)

    if data:
        prefix = bytes([data[0]])
        for byte in data[1:]:
            candidate = prefix + bytes([byte])
            if candidate in table:
                prefix = candidate
            else:
                w.write_bits(table[prefix], CODE_BITS)
                if next_code < MAX_CODES:
                    table[candidate] = next_code
                    next_code += 1
                else:
                    w.write_bits(CLEAR, CODE_BITS)
                    table = _new_table()
                    next_code = FIRST_CODE
                prefix = bytes([byte])
        w.write_bits(table[prefix], CODE_BITS)
    w.write_bits(END, CODE_BITS)

    out = bytearray()
    out += len(data).to_bytes(4, "big")
    out += w.get_bytes()
    return bytes(out)


def decode(buf):
    if len(buf) < 4:
        raise ValueError("truncated LZW header")
    total = int.from_bytes(buf[:4], "big")
    r = BitReader(buf[4:])
    if total == 0:
        return b""

    table = [bytes([i]) for i in range(256)]
    table += [b"", b""]          # placeholders for CLEAR / END
    out = bytearray()
    prev = None

    while len(out) < total:
        code = r.read_bits(CODE_BITS)
        if code == END:
            break
        if code == CLEAR:
            table = [bytes([i]) for i in range(256)]
            table += [b"", b""]
            next_code = FIRST_CODE
            prev = None
            continue
        if prev is None:
            entry = table[code]
            out += entry
            prev = entry
            continue
        if code < len(table):
            entry = table[code]
        else:
            # KwKw case: code references a phrase not yet added
            entry = prev + bytes([prev[0]])
        out += entry
        if len(table) < MAX_CODES:
            table.append(prev + bytes([entry[0]]))
        prev = entry
    return bytes(out)


def step_frames(data, limit=200):
    """Trace emitted codes and dictionary growth (for the visualiser)."""
    frames = []
    table = _new_table()
    next_code = FIRST_CODE
    if not data:
        return {"frames": [], "total": 0}
    prefix = bytes([data[0]])
    for byte in data[1:]:
        candidate = prefix + bytes([byte])
        if candidate in table:
            prefix = candidate
        else:
            if len(frames) < limit:
                frames.append({
                    "code": table[prefix],
                    "phrase": prefix.decode("latin-1"),
                    "added": candidate.decode("latin-1"),
                    "dict_size": next_code,
                })
            if next_code < MAX_CODES:
                table[candidate] = next_code
                next_code += 1
            else:
                table = _new_table()
                next_code = FIRST_CODE
            prefix = bytes([byte])
    if len(frames) < limit:
        frames.append({"code": table[prefix],
                       "phrase": prefix.decode("latin-1"),
                       "added": None, "dict_size": next_code})
    return {"frames": frames, "total": len(frames),
            "max_codes": MAX_CODES}
