"""PicoZip demo: compress a sample text with every algorithm and print the
results, verifying each round-trip.

Run from the project root:  python examples/compress_demo.py
"""

from picozip import codecs, container, bench


def main():
    text = ("PicoZip demonstrates five lossless compression algorithms. "
            "Lossless compression removes redundancy; the more a phrase "
            "repeats, the better it compresses. " * 40).encode("utf-8")

    print(f"Input: {len(text)} bytes")
    print(f"{'codec':<14}{'payload':>10}{'ratio':>9}{'roundtrip':>11}")
    print("-" * 46)
    for name in codecs.ORDER:
        meta = codecs.REGISTRY[name]
        payload = meta["encode"](text)
        ok = meta["decode"](payload) == text
        ratio = len(payload) / len(text)
        print(f"{meta['name']:<14}{len(payload):>10}{ratio:>9.3f}"
              f"{('OK' if ok else 'FAIL'):>11}")

    # .pz container round-trip
    blob = container.pack(text, "hybrid")
    assert container.unpack(blob) == text
    print(f"\n.pz file (hybrid): {len(blob)} bytes, "
          f"header verified, CRC-32 OK")


if __name__ == "__main__":
    main()
