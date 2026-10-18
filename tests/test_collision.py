import io
import unittest

from PIL import Image

from app.collision import (
    DATA_DIR,
    HEIGHT,
    WIDTH,
    build_file_pair,
    build_picture_pair,
    md5_hex,
    sha256_hex,
    visible_center,
)


def _png(color: tuple[int, int, int]) -> bytes:
    image = Image.new("RGB", (WIDTH, HEIGHT), color)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


class CollisionTests(unittest.TestCase):
    def test_picture_pair_shares_md5_and_shows_different_pixels(self) -> None:
        pair = build_picture_pair(_png((255, 0, 0)), _png((0, 0, 255)))
        first, second = pair["files"]
        self.assertEqual(md5_hex(first["data"]), md5_hex(second["data"]))
        self.assertNotEqual(sha256_hex(first["data"]), sha256_hex(second["data"]))
        self.assertEqual(visible_center(first["data"]), (255, 0, 0))
        self.assertEqual(visible_center(second["data"]), (0, 0, 255))
        self.assertTrue(pair["diff"])
        prefix_len = len((DATA_DIR / "gif_prefix.bin").read_bytes())
        self.assertEqual(first["data"][prefix_len + 128 :], second["data"][prefix_len + 128 :])
        self.assertNotEqual(
            first["data"][prefix_len : prefix_len + 128],
            second["data"][prefix_len : prefix_len + 128],
        )

    def test_file_pair_keeps_the_typed_suffix(self) -> None:
        text = "same ending, different block"
        pair = build_file_pair(text)
        first, second = pair["files"]
        self.assertEqual(md5_hex(first["data"]), md5_hex(second["data"]))
        self.assertNotEqual(first["data"], second["data"])
        self.assertNotEqual(sha256_hex(first["data"]), sha256_hex(second["data"]))
        self.assertTrue(first["data"].endswith(text.encode()))
        self.assertTrue(second["data"].endswith(text.encode()))
        self.assertEqual(first["data"][64 + 128 :], second["data"][64 + 128 :])

    def test_rejects_a_non_image(self) -> None:
        with self.assertRaises(ValueError):
            build_picture_pair(b"not an image", _png((0, 0, 0)))


if __name__ == "__main__":
    unittest.main()
