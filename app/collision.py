"""Build two different files that share one MD5.

The collision blocks were generated once with Marc Stevens' FastColl
(identical-prefix attack). This module only stitches those blocks into
a GIF pair or a plain file pair. It does not search for new collisions.
"""

from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

DATA_DIR = Path(__file__).resolve().parent / "data"
WIDTH = 640
HEIGHT = 360
MAX_UPLOAD_BYTES = 15 * 1024 * 1024

# 6x6x6 RGB cube (216 colors) plus 40 grays. Fixed so every upload
# uses the same GIF header, which is what the stored collision expects.
_LEVELS = (0, 51, 102, 153, 204, 255)


def _palette_bytes() -> bytes:
    colors: list[tuple[int, int, int]] = [
        (r, g, b) for r in _LEVELS for g in _LEVELS for b in _LEVELS
    ]
    for i in range(40):
        value = round(i * 255 / 39)
        colors.append((value, value, value))
    if len(colors) != 256:
        raise RuntimeError("palette must contain 256 colors")
    raw = bytearray()
    for red, green, blue in colors:
        raw.extend((red, green, blue))
    return bytes(raw)


PALETTE = _palette_bytes()


def md5_hex(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def comment_prefix(header: bytes) -> bytes:
    """Pad a GIF header so FastColl's last predictable difference is a comment length.

    FastColl flips the high bit of collision byte 123 and leaves the earlier
    comment payload free to absorb the other differences. A GIF comment
    sub-block length is one byte, so that single bit changes the length by 128.
    """
    base = header + b"\x21\xfe"
    while True:
        remainder = len(base) % 64
        if remainder == 63:
            prefix = base + bytes([0x7B])
            break
        delta = 62 - remainder
        if delta > 0:
            prefix = base + bytes([delta]) + (b" " * delta) + bytes([0x7B])
            break
        # A zero-length sub-block would end the comment. Shift by two bytes.
        base += b"\x01 "
    if len(prefix) % 64 != 0:
        raise RuntimeError("collision prefix is not 64-byte aligned")
    return prefix


def first_graphic_control(gif: bytes) -> int:
    if not gif.startswith(b"GIF89a"):
        raise ValueError("expected a GIF89a header")
    packed = gif[10]
    if not packed & 0x80:
        raise ValueError("expected a global color table")
    offset = 13 + 3 * (2 << (packed & 7))
    while offset < len(gif):
        separator = gif[offset]
        if separator == 0x21 and gif[offset + 1] == 0xF9:
            return offset
        if separator == 0x21:
            offset += 2
            while True:
                size = gif[offset]
                offset += 1 + size
                if size == 0:
                    break
            continue
        raise ValueError(f"unexpected GIF block {separator:#x} at offset {offset}")
    raise ValueError("GIF has no graphic control extension")


def _load_meta() -> dict:
    return json.loads((DATA_DIR / "meta.json").read_text(encoding="utf-8"))


def _load_pair(stem: str) -> tuple[bytes, bytes, bytes]:
    prefix = (DATA_DIR / f"{stem}_prefix.bin").read_bytes()
    block_a = (DATA_DIR / f"{stem}_block_a.bin").read_bytes()
    block_b = (DATA_DIR / f"{stem}_block_b.bin").read_bytes()
    if len(block_a) != 128 or len(block_b) != 128:
        raise RuntimeError(f"{stem} collision blocks must be 128 bytes")
    return prefix, block_a, block_b


def differing_bytes(left: bytes, right: bytes) -> list[dict[str, int]]:
    if len(left) != len(right):
        raise ValueError("collision blocks differ in length")
    return [
        {"offset": index, "left": left[index], "right": right[index]}
        for index in range(len(left))
        if left[index] != right[index]
    ]


def _ordered_blocks(block_a: bytes, block_b: bytes) -> tuple[bytes, bytes]:
    """Return (shows picture 1, shows picture 2).

    The smaller length byte ends the comment before both frames, so a viewer
    stays on the first picture. The larger length swallows the first picture.
    """
    if (block_a[123] ^ block_b[123]) == 0x80 and block_a[123] < block_b[123]:
        return block_a, block_b
    if (block_b[123] ^ block_a[123]) == 0x80 and block_b[123] < block_a[123]:
        return block_b, block_a
    raise RuntimeError("stored blocks do not have the FastColl length-byte difference")


def _gif_suffix(frame_bytes: bytes, short_length: int) -> bytes:
    if short_length < 4:
        raise RuntimeError("comment length is too small to finish the collision block")
    # Four comment bytes already sit at the end of the collision block.
    suffix = b" " * (short_length - 4)
    suffix += bytes([0x80]) + (b" " * 0x7F)
    suffix += bytes([0x14, 0x00])
    suffix += frame_bytes
    return suffix


def _palette_image() -> Image.Image:
    image = Image.new("P", (1, 1))
    image.putpalette(PALETTE)
    return image


def normalize_image(raw: bytes) -> Image.Image:
    if len(raw) > MAX_UPLOAD_BYTES:
        raise ValueError("Image is larger than 15 MB")
    try:
        opened = Image.open(io.BytesIO(raw))
        opened.load()
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError("Could not read that file as an image") from exc
    rgb = ImageOps.exif_transpose(opened).convert("RGB")
    fitted = ImageOps.contain(rgb, (WIDTH, HEIGHT), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))
    canvas.paste(
        fitted,
        ((WIDTH - fitted.width) // 2, (HEIGHT - fitted.height) // 2),
    )
    return canvas.quantize(palette=_palette_image(), dither=Image.Dither.NONE)


def render_source_gif(first: Image.Image, second: Image.Image) -> bytes:
    """Two-frame GIF. Frame 1 delay is the GIF maximum, about 11 minutes."""
    buffer = io.BytesIO()
    first.save(
        buffer,
        format="GIF",
        save_all=True,
        append_images=[second],
        duration=[655350, 100],
        loop=0,
        disposal=2,
        optimize=False,
    )
    return buffer.getvalue()


def build_picture_pair(first_bytes: bytes, second_bytes: bytes) -> dict:
    first = normalize_image(first_bytes)
    second = normalize_image(second_bytes)
    source = render_source_gif(first, second)
    frame_at = first_graphic_control(source)
    meta = _load_meta()
    prefix, block_a, block_b = _load_pair("gif")
    header_len = int(meta["gif_header_len"])
    if frame_at != header_len or source[:header_len] != prefix[:header_len]:
        raise RuntimeError("GIF header does not match the precomputed collision prefix")
    show_first, show_second = _ordered_blocks(block_a, block_b)
    suffix = _gif_suffix(source[frame_at:], show_first[123])
    picture_one = prefix + show_first + suffix
    picture_two = prefix + show_second + suffix
    if md5_hex(picture_one) != md5_hex(picture_two):
        raise RuntimeError("picture pair does not share an MD5")
    return {
        "md5": md5_hex(picture_one),
        "kind": "gif",
        "files": [
            _file_record("picture-1.gif", picture_one, "image/gif"),
            _file_record("picture-2.gif", picture_two, "image/gif"),
        ],
        "diff": differing_bytes(show_first, show_second),
        "blocks": {
            "left": list(show_first),
            "right": list(show_second),
        },
    }


def build_file_pair(text: str) -> dict:
    if len(text) > 20000:
        raise ValueError("Shared text is limited to 20,000 characters")
    suffix = text.encode("utf-8")
    prefix, block_a, block_b = _load_pair("bin")
    left = prefix + block_a + suffix
    right = prefix + block_b + suffix
    if md5_hex(left) != md5_hex(right):
        raise RuntimeError("file pair does not share an MD5")
    return {
        "md5": md5_hex(left),
        "kind": "bin",
        "files": [
            _file_record("file-1.bin", left, "application/octet-stream"),
            _file_record("file-2.bin", right, "application/octet-stream"),
        ],
        "diff": differing_bytes(block_a, block_b),
        "blocks": {
            "left": list(block_a),
            "right": list(block_b),
        },
    }


def _file_record(name: str, data: bytes, media_type: str) -> dict:
    return {
        "name": name,
        "media_type": media_type,
        "size": len(data),
        "sha256": sha256_hex(data),
        "data": data,
    }


def visible_center(gif: bytes) -> tuple[int, int, int]:
    image = Image.open(io.BytesIO(gif))
    rgb = image.convert("RGB")
    return rgb.getpixel((WIDTH // 2, HEIGHT // 2))
