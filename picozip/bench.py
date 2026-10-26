"""Compression ratio and speed micro-benchmarks.

Reports, per codec, the raw payload size, the full .pz file size (including
the 20-byte header), best-of timing, and the Shannon zero-order lower bound
for comparison.  Small teaching tool, not a rigorous benchmark suite.
"""

import random
import time

from . import codecs
from .container import HEADER, pack
from .entropy import entropy_bits, entropy_bits_per_byte

_TEXT = (
    "Compression works by removing redundancy.  A text file repeats common "
    "letters and whole words, so a dictionary coder can replace repeated "
    "phrases with short references.  Random bytes carry no redundancy at all, "
    "and no lossless codec can shrink them; indeed any complete compression "
    "scheme must make some inputs longer.  Huffman codes assign short bit "
    "strings to frequent symbols, while LZ77 searches a sliding window for a "
    "previous occurrence and emits a distance and a length.  Combining the "
    "two ideas is the core of the DEFLATE family used by zlib and gzip.\n\n"
) * 12

_rng = random.Random(7)
_SAMPLES = {
    "text": _TEXT.encode(),
    "repetitive": (b"ABCABCABC" * 1200 + b"AAAA" * 300),
    "runs": (b"\x00" * 2000 + b"\xff" * 1500 + b"ab" * 1000),
    "random": bytes(_rng.randrange(256) for _ in range(6000)),
}


def _best_ms(fn, repeat=3):
    best = None
    for _ in range(repeat):
        t0 = time.perf_counter()
        fn()
        dt = (time.perf_counter() - t0) * 1000.0
        best = dt if best is None else min(best, dt)
    return round(best, 4)


def bench_data(data, algos=None):
    algos = algos or codecs.ORDER
    rows = []
    for algo in algos:
        meta = codecs.REGISTRY[algo]
        encoded = meta["encode"](data)
        packed = pack(data, algo)
        rows.append({
            "codec": algo,
            "name": meta["name"],
            "payload_size": len(encoded),
            "file_size": len(packed),
            "payload_ratio": round(len(encoded) / len(data), 4) if data else None,
            "ratio": round(len(packed) / len(data), 4) if data else None,
            "encode_ms": _best_ms(lambda a=algo: codecs.encode(data, a)),
            "decode_ms": _best_ms(lambda a=algo: codecs.decode(encoded, a)),
            "roundtrip": meta["decode"](encoded) == data,
        })
    ideal_bytes = entropy_bits(data) / 8.0
    return {
        "original_size": len(data),
        "entropy_bits_per_byte": round(entropy_bits_per_byte(data), 4),
        "ideal_bytes": round(ideal_bytes, 2),
        "header_bytes": HEADER,
        "rows": rows,
    }


def bench_samples():
    return {name: bench_data(data) for name, data in _SAMPLES.items()}


def _format(result):
    n = result["original_size"]
    print(f"\noriginal {n} bytes, entropy "
          f"{result['entropy_bits_per_byte']} bits/byte, "
          f"ideal ~{result['ideal_bytes']} bytes")
    print(f"{'codec':<14}{'payload':>10}{'ratio':>9}"
          f"{'enc ms':>10}{'dec ms':>10}")
    for r in result["rows"]:
        ratio = "-" if r["ratio"] is None else f"{r['ratio']:.3f}"
        print(f"{r['name']:<14}{r['payload_size']:>10}{ratio:>9}"
              f"{r['encode_ms']:>10.2f}{r['decode_ms']:>10.2f}")


def main():
    for name, result in bench_samples().items():
        print(f"=== {name} ===")
        _format(result)


if __name__ == "__main__":
    main()
