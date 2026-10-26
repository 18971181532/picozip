"""Static canonical Huffman coding.

The byte stream is treated as a zero-order source.  We build a Huffman tree
with a binary heap, read off the code lengths, then emit *canonical* codes
from the lengths (so the decoder only needs the per-symbol lengths, not the
whole tree).  The header stores one length byte for every possible symbol
(0..255); the payload is packed bits.  A single-symbol input gets one bit
per symbol, and the empty input is handled explicitly.
"""

import heapq

from .bits import BitWriter, BitReader
from .entropy import frequencies


# ---------------------------------------------------------------------------
# Lengths
# ---------------------------------------------------------------------------
def code_lengths(freqs):
    """Return a list of code lengths (one per symbol; 0 if absent)."""
    lengths = [0] * len(freqs)
    leaves = [(b, f) for b, f in enumerate(freqs) if f]
    if not leaves:
        return lengths
    if len(leaves) == 1:
        lengths[leaves[0][0]] = 1
        return lengths

    # node array: [weight, left, right] ; leaves are represented by a
    # symbol id >= 0 encoded as negative-ish via None children.
    # heap entries: (weight, tie, node_index)
    nodes = []          # index -> dict
    heap = []
    tie = 0
    for b, f in leaves:
        idx = len(nodes)
        nodes.append({"sym": b, "left": None, "right": None, "weight": f})
        heapq.heappush(heap, (f, tie, idx))
        tie += 1

    while len(heap) > 1:
        wa, _, ia = heapq.heappop(heap)
        wb, _, ib = heapq.heappop(heap)
        idx = len(nodes)
        nodes.append({"sym": None, "left": ia, "right": ib,
                      "weight": wa + wb})
        heapq.heappush(heap, (wa + wb, tie, idx))
        tie += 1

    root = heap[0][2]

    def walk(node, depth):
        if depth > 255:
            raise ValueError("Huffman tree too deep")
        nd = nodes[node]
        if nd["sym"] is not None:
            lengths[nd["sym"]] = depth
            return
        walk(nd["left"], depth + 1)
        walk(nd["right"], depth + 1)

    walk(root, 0)
    return lengths


def canonical_codes(lengths):
    """Map symbol -> integer code for the given code lengths."""
    present = sorted((length, b) for b, length in enumerate(lengths)
                     if length)
    codes = {}
    code = 0
    prev_len = 0
    for length, b in present:
        code <<= (length - prev_len)
        codes[b] = (code, length)
        code += 1
        prev_len = length
    return codes


# ---------------------------------------------------------------------------
# Encode / decode
# ---------------------------------------------------------------------------
def encode(data):
    freqs = frequencies(data)
    lengths = code_lengths(freqs)
    out = bytearray()
    out += len(data).to_bytes(4, "big")
    out += bytes(lengths)          # 256 length bytes

    w = BitWriter()
    if data:
        codes = canonical_codes(lengths)
        for b in data:
            code, length = codes[b]
            w.write_bits(code, length)
    out += w.get_bytes()
    return bytes(out)


def decode(buf):
    if len(buf) < 4 + 256:
        raise ValueError("truncated Huffman header")
    total = int.from_bytes(buf[:4], "big")
    lengths = list(buf[4:4 + 256])
    payload = buf[4 + 256:]

    if total == 0:
        return b""

    codes = canonical_codes(lengths)
    max_len = max(lengths)
    # Fast lookup table indexed by the next max_len bits.
    table = [None] * (1 << max_len)
    for sym, (code, length) in codes.items():
        pad = max_len - length
        base = code << pad
        for suffix in range(1 << pad):
            table[base | suffix] = (sym, length)

    r = BitReader(payload)
    out = bytearray()
    for _ in range(total):
        window = r.read_bits(max_len)
        entry = table[window]
        if entry is None:
            raise ValueError("invalid Huffman code")
        sym, length = entry
        out.append(sym)
        r.rewind(max_len - length)   # consume only the symbol's code
    return bytes(out)


# ---------------------------------------------------------------------------
# Visualisation
# ---------------------------------------------------------------------------
def _heap_merges(freqs):
    """Return (nodes, root, merges) for the heap construction."""
    leaves = [(b, f) for b, f in enumerate(freqs) if f]
    nodes = []
    heap = []
    tie = 0
    for b, f in leaves:
        idx = len(nodes)
        nodes.append({"id": idx, "sym": b, "left": None, "right": None,
                      "weight": f})
        heapq.heappush(heap, (f, tie, idx))
        tie += 1
    merges = []
    while len(heap) > 1:
        wa, _, ia = heapq.heappop(heap)
        wb, _, ib = heapq.heappop(heap)
        idx = len(nodes)
        nodes.append({"id": idx, "sym": None, "left": ia, "right": ib,
                      "weight": wa + wb})
        merges.append({"a": ia, "b": ib, "node": idx, "weight": wa + wb})
        heapq.heappush(heap, (wa + wb, tie, idx))
        tie += 1
    root = heap[0][2] if heap else None
    return nodes, root, merges


def analyze(data, max_nodes=200):
    """Build frequencies, codes, a laid-out tree and code table."""
    freqs = frequencies(data)
    total = len(data)
    if total == 0:
        return {"frequencies": freqs, "codes": [], "tree": {"nodes": [],
                "edges": []}, "entropy": 0.0, "mean_length": 0.0,
                "merges": []}

    nodes, root, merges = _heap_merges(freqs)
    lengths = code_lengths(freqs)
    codes = canonical_codes(lengths)

    # tidy layout: leaves get x by in-order traversal, y = depth
    positions = {}
    counter = [0]

    def place(node, depth):
        nd = nodes[node]
        if nd["sym"] is not None:
            positions[node] = (counter[0], depth)
            counter[0] += 1
            return
        place(nd["left"], depth + 1)
        place(nd["right"], depth + 1)
        lx = positions[nd["left"]][0]
        rx = positions[nd["right"]][0]
        positions[node] = ((lx + rx) / 2.0, depth)

    place(root, 0)

    vis_nodes = []
    for nd in nodes:
        x, y = positions[nd["id"]]
        vis_nodes.append({
            "id": nd["id"],
            "symbol": nd["sym"],
            "weight": nd["weight"],
            "x": x, "y": y,
            "leaf": nd["sym"] is not None,
        })
    edges = []
    for nd in nodes:
        if nd["left"] is not None:
            edges.append({"from": nd["id"], "to": nd["left"], "bit": 0})
            edges.append({"from": nd["id"], "to": nd["right"], "bit": 1})

    mean_length = sum(freqs[b] * lengths[b] for b in range(256)) / total
    table = sorted(
        ({"symbol": b, "count": freqs[b], "length": lengths[b],
          "code": format(codes[b][0], "0{}b".format(lengths[b]))}
         for b in codes),
        key=lambda d: (d["length"], d["symbol"]))
    from .entropy import entropy_bits_per_byte
    return {
        "frequencies": freqs,
        "codes": table,
        "tree": {"nodes": vis_nodes, "edges": edges},
        "merges": merges,
        "mean_length": mean_length,
        "entropy": entropy_bits_per_byte(data),
    }
