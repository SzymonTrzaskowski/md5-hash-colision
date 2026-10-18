"""Generate the FastColl blocks stored in app/data.

Clones of this repo do not need to run this. The blocks are already saved.
Regeneration needs the educational fastcoll driver:

    python tools/build_blocks.py --fastcoll path/to/fastcoll-driver.exe

FastColl is Marc Stevens' identical-prefix MD5 collision tool (2006).
Its license does not allow redistributing the program, so only the
128-byte results are committed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.collision import (  # noqa: E402
    DATA_DIR,
    PALETTE,
    comment_prefix,
    first_graphic_control,
    md5_hex,
    render_source_gif,
)
from PIL import Image


def _solid(color: tuple[int, int, int]) -> Image.Image:
    from app.collision import HEIGHT, WIDTH, _palette_image

    rgb = Image.new("RGB", (WIDTH, HEIGHT), color)
    return rgb.quantize(palette=_palette_image(), dither=Image.Dither.NONE)


def _run_fastcoll(fastcoll: Path, prefix: bytes) -> tuple[bytes, bytes]:
    with tempfile.TemporaryDirectory() as folder:
        work = Path(folder)
        prefix_path = work / "prefix.bin"
        out1 = work / "out1.bin"
        out2 = work / "out2.bin"
        prefix_path.write_bytes(prefix)
        subprocess.check_call([str(fastcoll), str(prefix_path), str(out1), str(out2)])
        file1 = out1.read_bytes()
        file2 = out2.read_bytes()
    if not file1.startswith(prefix) or not file2.startswith(prefix):
        raise SystemExit("fastcoll output does not start with the prefix")
    block1 = file1[len(prefix) :]
    block2 = file2[len(prefix) :]
    if len(block1) != 128 or len(block2) != 128:
        raise SystemExit("fastcoll did not append 128-byte blocks")
    if hashlib.md5(file1).digest() != hashlib.md5(file2).digest():
        raise SystemExit("fastcoll outputs do not collide")
    if block1[123] ^ block2[123] != 0x80:
        raise SystemExit("byte 123 is not the expected FastColl difference")
    print(f"  md5 {md5_hex(file1)}  byte123 {block1[123]:02x} vs {block2[123]:02x}")
    return block1, block2


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fastcoll", required=True, type=Path)
    args = parser.parse_args()
    if not args.fastcoll.is_file():
        raise SystemExit(f"fastcoll not found: {args.fastcoll}")

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    source = render_source_gif(_solid((255, 0, 0)), _solid((0, 0, 255)))
    header_len = first_graphic_control(source)
    if source[13 : 13 + 768] != PALETTE:
        raise SystemExit("rendered GIF palette does not match the fixed palette")
    gif_prefix = comment_prefix(source[:header_len])
    print(f"GIF prefix {len(gif_prefix)} bytes, header {header_len}")
    print("Computing GIF collision blocks...")
    gif_a, gif_b = _run_fastcoll(args.fastcoll, gif_prefix)

    bin_prefix = b"MD5 collision demo. Shared prefix ends here.\n".ljust(64, b"\0")
    print("Computing generic file collision blocks...")
    bin_a, bin_b = _run_fastcoll(args.fastcoll, bin_prefix)

    (DATA_DIR / "gif_prefix.bin").write_bytes(gif_prefix)
    (DATA_DIR / "gif_block_a.bin").write_bytes(gif_a)
    (DATA_DIR / "gif_block_b.bin").write_bytes(gif_b)
    (DATA_DIR / "bin_prefix.bin").write_bytes(bin_prefix)
    (DATA_DIR / "bin_block_a.bin").write_bytes(bin_a)
    (DATA_DIR / "bin_block_b.bin").write_bytes(bin_b)
    (DATA_DIR / "meta.json").write_text(
        json.dumps({"gif_header_len": header_len}, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote blocks to {DATA_DIR}")


if __name__ == "__main__":
    main()
