"""Byte frequency analysis and Shannon entropy.

The Shannon entropy is the theoretical lower bound on the average number
of bits per symbol for a memoryless (zero-order) code such as Huffman.  It
is a useful yardstick when judging how much redundancy a real codec leaves
on the table.
"""

import math
from collections import Counter

ALPHABET = 256


def frequencies(data):
    """Return a length-256 list of byte counts."""
    counts = [0] * ALPHABET
    for b in data:
        counts[b] += 1
    return counts


def entropy_bits_per_byte(data):
    """Zero-order Shannon entropy, in bits per byte (0.0 for empty input)."""
    if not data:
        return 0.0
    n = len(data)
    h = 0.0
    for c in Counter(data).values():
        p = c / n
        h -= p * math.log2(p)
    return h


def entropy_bits(data):
    """Total information content in bits (entropy * length)."""
    return entropy_bits_per_byte(data) * len(data)


def redundancy(data):
    """How many bits per byte are above the entropy limit (max 8)."""
    return 8.0 - entropy_bits_per_byte(data) if data else 0.0


def top_symbols(data, limit=16):
    """Return the most frequent ``(byte, count, probability)`` entries."""
    n = len(data)
    if not n:
        return []
    top = Counter(data).most_common(limit)
    return [{"byte": b, "count": c, "prob": c / n} for b, c in top]
