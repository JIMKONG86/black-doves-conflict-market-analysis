import struct
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ASSET_DIRECTORY = PROJECT_ROOT / "assets"


def _png_dimensions(path):
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
        raise ValueError(f"Not a valid PNG header: {path}")
    return struct.unpack(">II", data[16:24])


class TestBlackDovesLogoAssets(unittest.TestCase):
    def test_active_logo_is_the_high_resolution_dark_mode_variant(self):
        active = ASSET_DIRECTORY / "black_doves_logo.png"
        dark = ASSET_DIRECTORY / "black_doves_logo_dark.png"

        self.assertEqual(_png_dimensions(active), (2048, 989))
        self.assertEqual(active.read_bytes(), dark.read_bytes())

    def test_dark_mode_logo_is_not_the_black_light_mode_variant(self):
        dark = ASSET_DIRECTORY / "black_doves_logo_dark.png"
        light = ASSET_DIRECTORY / "black_doves_logo_light.png"

        self.assertNotEqual(dark.read_bytes(), light.read_bytes())
        self.assertTrue((ASSET_DIRECTORY / "black_doves_logo_print.png").is_file())
        self.assertTrue((ASSET_DIRECTORY / "black_doves_logo_legacy.png").is_file())


if __name__ == "__main__":
    unittest.main()
