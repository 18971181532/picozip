"""The PicoZip ``.pz`` container.

Header (20 bytes, big-endian):

    offset  size  field
      0      2    magic b'PZ'
      2      1    version (1)
      3      1    codec id
      4      8    original length
     12      4    CRC-32 of the original data
     16      4    payload length
     20     ...   codec payload

A CRC mismatch on extraction raises ``IntegrityError``.
"""

import zlib

from . import codecs

MAGIC = b"PZ"
VERSION = 1
HEADER = 20


class IntegrityError(Exception):
    """Raised when the stored checksum does not match the data."""


def pack(data, algo):
    codec = codecs.normalize(algo)
    payload = codecs.encode(data, codec)
    cid = codecs.REGISTRY[codec]["id"]
    out = bytearray()
    out += MAGIC
    out.append(VERSION)
    out.append(cid)
    out += len(data).to_bytes(8, "big")
    out += zlib.crc32(data).to_bytes(4, "big")
    out += len(payload).to_bytes(4, "big")
    out += payload
    return bytes(out)


def inspect(blob):
    if len(blob) < HEADER or blob[:2] != MAGIC:
        raise ValueError("not a PicoZip (.pz) file (bad magic)")
    version = blob[2]
    cid = blob[3]
    original = int.from_bytes(blob[4:12], "big")
    crc = int.from_bytes(blob[12:16], "big")
    payload_len = int.from_bytes(blob[16:20], "big")
    algo = codecs.BY_ID.get(cid, f"unknown({cid})")
    return {
        "version": version,
        "codec_id": cid,
        "codec": algo,
        "original_size": original,
        "crc32": crc,
        "payload_size": payload_len,
        "total_size": HEADER + payload_len,
        "ratio": round((HEADER + payload_len) / original, 4)
        if original else None,
    }


def unpack(blob, verify=True):
    info = inspect(blob)
    if not isinstance(info["codec"], str) or info["codec"].startswith("unknown"):
        raise ValueError(f"unsupported codec id {info['codec_id']}")
    payload = blob[HEADER:HEADER + info["payload_size"]]
    if len(payload) != info["payload_size"]:
        raise ValueError("truncated payload")
    data = codecs.decode(payload, info["codec"])
    if len(data) != info["original_size"]:
        raise IntegrityError("decompressed length mismatch")
    if verify and zlib.crc32(data) != info["crc32"]:
        raise IntegrityError("CRC-32 mismatch: data is corrupt")
    return data
