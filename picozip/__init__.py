"""PicoZip — a zero-dependency, multi-algorithm compression laboratory.

RLE, canonical Huffman, LZSS, LZW and a DEFLATE-like LZSS+Huffman hybrid,
all built on the standard library, with a .pz container, CLI, benchmarks
and an animated Canvas workbench.
"""

__version__ = "0.1.0"

from . import codecs, container, huffman, lzss, lzw, rle, hybrid, entropy

__all__ = ["codecs", "container", "huffman", "lzss", "lzw", "rle",
           "hybrid", "entropy", "__version__"]
