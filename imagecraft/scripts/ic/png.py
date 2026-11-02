"""Small strict PNG8 decoder/verifier for the dependency-free cloud client."""
from __future__ import annotations

import struct
import zlib

from .common import Error

SIGNATURE = b"\x89PNG\r\n\x1a\n"
LIMIT = 32 * 1024 * 1024


def decode(data: bytes) -> tuple[bytes, int, int]:
    """Decode/unfilter non-interlaced PNG8; return a metadata-stripped PNG and size.

    Unsupported formats fail explicitly. This does not claim to decode JPEG/WebP.
    Both compressed input and decompressed scanlines have hard size bounds.
    """
    if not data.startswith(SIGNATURE) or not 45 <= len(data) <= LIMIT:
        raise Error("A final PNG file no larger than 32 MiB is required")
    offset, chunks, idat = 8, [], bytearray()
    width = height = channels = color = 0
    ended = False
    saw_data = False
    data_ended = False
    palette_entries = 0
    for _ in range(10000):
        if offset + 12 > len(data):
            raise Error("Truncated PNG chunk")
        size = struct.unpack_from(">I", data, offset)[0]
        kind = data[offset + 4:offset + 8]
        if not all(65 <= value <= 90 or 97 <= value <= 122 for value in kind) or kind[2] & 32:
            raise Error("Invalid PNG chunk type")
        end = offset + size + 12
        if end > len(data):
            raise Error("Truncated PNG payload")
        body = data[offset + 8:end - 4]
        crc = struct.unpack_from(">I", data, end - 4)[0]
        if zlib.crc32(kind + body) & 0xffffffff != crc:
            raise Error("PNG CRC mismatch")
        if offset == 8 and kind != b"IHDR":
            raise Error("PNG must start with IHDR")
        if saw_data and kind != b"IDAT":
            data_ended = True
        if kind == b"IHDR":
            if width or size != 13:
                raise Error("Invalid PNG header")
            width, height, depth, color, compression, filtering, interlace = struct.unpack(">IIBBBBB", body)
            channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}.get(color, 0)
            if not (0 < width and 0 < height and width * height <= 24_000_000 and depth == 8 and channels
                    and compression == 0 and filtering == 0 and interlace == 0):
                raise Error("Cloud client supports PNG8 without interlacing, up to 24 megapixels")
        elif kind == b"PLTE":
            if saw_data or palette_entries or color in (0, 4) or not 0 < size <= 768 or size % 3:
                raise Error("Invalid PNG palette")
            palette_entries = size // 3
        elif kind == b"tRNS":
            if saw_data or (color == 3 and not 0 < size <= palette_entries) or (color == 0 and size != 2) or (color == 2 and size != 6) or color in (4, 6):
                raise Error("Invalid PNG transparency")
        elif kind == b"IDAT":
            if data_ended or color == 3 and not palette_entries:
                raise Error("Invalid PNG image-data ordering or missing palette")
            saw_data = True
            idat.extend(body)
        elif kind == b"IEND":
            if size or not saw_data or end != len(data):
                raise Error("Invalid PNG end")
            ended = True
        elif kind[0] & 32 == 0 and kind != b"PLTE":
            raise Error("Unsupported critical PNG chunk")
        # Keep only pixel data and transparency. Unknown ancillary chunks may
        # carry private paths too; a blacklist of known text tags is not enough.
        if kind in (b"IHDR", b"PLTE", b"tRNS", b"IDAT", b"IEND"):
            chunks.append(data[offset:end])
        offset = end
        if ended:
            break
    if not ended:
        raise Error("Missing PNG end")
    stride = width * channels
    expected = height * (stride + 1)
    dec = zlib.decompressobj()
    try:
        raw = dec.decompress(bytes(idat), expected + 1)
    except zlib.error:
        raise Error("PNG decompression failed") from None
    if len(raw) != expected or not dec.eof or dec.unused_data or dec.unconsumed_tail:
        raise Error("PNG scanline length or compression stream invalid")
    previous = bytearray(stride)
    for y in range(height):
        start = y * (stride + 1)
        method = raw[start]
        if method > 4:
            raise Error("Invalid PNG scanline filter")
        row = bytearray(raw[start + 1:start + 1 + stride])
        for x in range(stride):
            a = row[x - channels] if x >= channels else 0
            b = previous[x]
            c = previous[x - channels] if x >= channels else 0
            if method == 1:
                value = a
            elif method == 2:
                value = b
            elif method == 3:
                value = (a + b) // 2
            elif method == 4:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                value = a if pa <= pb and pa <= pc else b if pb <= pc else c
            else:
                value = 0
            row[x] = (row[x] + value) & 255
        if color == 3 and max(row) >= palette_entries:
            raise Error("PNG palette index out of range")
        previous = row
    return SIGNATURE + b"".join(chunks), width, height
