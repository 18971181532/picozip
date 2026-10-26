"""Command-line interface for PicoZip."""

import argparse
import json
import sys

from . import __version__
from . import codecs, container, bench
from .entropy import entropy_bits_per_byte, top_symbols


def _human_size(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.1f}{unit}" if unit != "B" else f"{n}B"
        n /= 1024.0


def build_parser():
    parser = argparse.ArgumentParser(
        prog="picozip",
        description="PicoZip: a zero-dependency multi-algorithm compression "
                    "laboratory (RLE / Huffman / LZSS / LZW / hybrid).")
    parser.add_argument("--version", action="version",
                        version=f"picozip {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("compress", help="compress a file")
    p.add_argument("file")
    p.add_argument("-a", "--algo", default="hybrid",
                   choices=codecs.ORDER, help="codec (default hybrid)")
    p.add_argument("-o", "--output")

    p = sub.add_parser("decompress", help="decompress a .pz file")
    p.add_argument("file")
    p.add_argument("-o", "--output")

    p = sub.add_parser("inspect", help="show a .pz header")
    p.add_argument("file")
    p.add_argument("--json", action="store_true")

    p = sub.add_parser("entropy", help="byte frequency / Shannon entropy")
    p.add_argument("file")
    p.add_argument("--json", action="store_true")

    sub.add_parser("codecs", help="list available codecs")

    p = sub.add_parser("bench", help="benchmark every codec")
    p.add_argument("file", nargs="?", help="optional file to benchmark")
    p.add_argument("--json", action="store_true")

    p = sub.add_parser("serve", help="launch the visual workbench")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8858)

    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    cmd = args.command

    if cmd == "serve":
        from .server import serve
        serve(args.host, args.port)
        return 0

    if cmd == "codecs":
        for key in codecs.ORDER:
            meta = codecs.REGISTRY[key]
            print(f"{meta['id']:>2}  {key:<8} {meta['desc']}")
        return 0

    if cmd == "compress":
        with open(args.file, "rb") as fh:
            data = fh.read()
        blob = container.pack(data, args.algo)
        out = args.output or args.file + ".pz"
        with open(out, "wb") as fh:
            fh.write(blob)
        ratio = len(blob) / len(data) if data else 0
        print(f"{args.algo}: {_human_size(len(data))} -> {out} "
              f"({_human_size(len(blob))}, ratio {ratio:.3f})")
        return 0

    if cmd == "decompress":
        with open(args.file, "rb") as fh:
            blob = fh.read()
        data = container.unpack(blob)
        out = args.output or (
            args.file[:-3] if args.file.endswith(".pz") else args.file + ".out")
        with open(out, "wb") as fh:
            fh.write(data)
        print(f"ok: {args.file} -> {out} ({_human_size(len(data))})")
        return 0

    if cmd == "inspect":
        with open(args.file, "rb") as fh:
            blob = fh.read()
        info = container.inspect(blob)
        if args.json:
            print(json.dumps(info, ensure_ascii=False, indent=2))
        else:
            for key in ("codec", "codec_id", "version", "original_size",
                        "payload_size", "total_size", "ratio", "crc32"):
                print(f"{key:<14}: {info[key]}")
        return 0

    if cmd == "entropy":
        with open(args.file, "rb") as fh:
            data = fh.read()
        info = {
            "file": args.file,
            "size": len(data),
            "entropy_bits_per_byte": round(entropy_bits_per_byte(data), 4),
            "ideal_bytes": round(entropy_bits_per_byte(data) * len(data) / 8, 1),
            "top_symbols": top_symbols(data, 12),
        }
        if args.json:
            print(json.dumps(info, ensure_ascii=False, indent=2))
        else:
            print(f"size {info['size']} bytes")
            print(f"entropy {info['entropy_bits_per_byte']} bits/byte")
            print(f"zero-order ideal ~{info['ideal_bytes']} bytes")
            for s in info["top_symbols"]:
                ch = s["byte"]
                shown = chr(ch) if 32 <= ch < 127 else "·"
                print(f"  {shown!r:>6} (0x{ch:02x})  {s['count']:>7}"
                      f"  {s['prob']:.4f}")
        return 0

    if cmd == "bench":
        if args.file:
            with open(args.file, "rb") as fh:
                data = fh.read()
            result = {"file": args.file, "result": bench.bench_data(data)}
        else:
            result = {"samples": bench.bench_samples()}
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            if "samples" in result:
                for name, r in result["samples"].items():
                    print(f"=== {name} ===")
                    bench._format(r)
            else:
                bench._format(result["result"])
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
