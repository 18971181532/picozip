"""Codec registry.

Maps a short algorithm name to an integer id and a pair of
``encode(data) -> payload`` / ``decode(payload) -> data`` functions.  The
container format stores the id so a file can be decompressed without the
caller naming the codec.
"""

from . import rle, huffman, lzss, lzw, hybrid

RLE = 1
HUFFMAN = 2
LZSS = 3
LZW = 4
HYBRID = 5

ORDER = ["rle", "huffman", "lzss", "lzw", "hybrid"]

REGISTRY = {
    "rle": {"id": RLE, "name": "RLE",
            "desc": "Run-length encoding (best for repeated bytes)",
            "encode": rle.encode, "decode": rle.decode},
    "huffman": {"id": HUFFMAN, "name": "Huffman",
                "desc": "Static canonical Huffman (zero-order)",
                "encode": huffman.encode, "decode": huffman.decode},
    "lzss": {"id": LZSS, "name": "LZSS",
             "desc": "LZ77 sliding window with hash chains",
             "encode": lambda d: lzss.encode(d)[0],
             "decode": lzss.decode},
    "lzw": {"id": LZW, "name": "LZW",
            "desc": "Lempel-Ziv-Welch dictionary (12-bit, clear code)",
            "encode": lzw.encode, "decode": lzw.decode},
    "hybrid": {"id": HYBRID, "name": "LZSS+Huffman",
               "desc": "DEFLATE-like two-stage coder",
               "encode": hybrid.encode, "decode": hybrid.decode},
}

BY_ID = {meta["id"]: key for key, meta in REGISTRY.items()}


def encode(data, algo):
    return REGISTRY[algo]["encode"](data)


def decode(payload, algo):
    return REGISTRY[algo]["decode"](payload)


def normalize(name):
    """Resolve a name or id to a registry key, or raise ValueError."""
    if name in REGISTRY:
        return name
    if isinstance(name, int) and name in BY_ID:
        return BY_ID[name]
    raise ValueError(f"unknown codec: {name!r} (choose from {ORDER})")
