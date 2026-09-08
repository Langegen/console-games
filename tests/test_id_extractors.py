"""Тесты извлечения Title ID, Serial и Disc ID."""
import unittest
from core.id_extractors import (
    extract_psp_id,
    extract_ps1_id,
    extract_wii_id,
    extract_gamecube_id,
    extract_wiiu_id,
    extract_platform_id
)


class TestIdExtractors(unittest.TestCase):

    def test_psp_id(self):
        self.assertEqual(extract_psp_id("Код диска: ULES-00123"), "ULES-00123")
        self.assertEqual(extract_psp_id("ULUS01234_Game.iso"), "ULUS-01234")
        self.assertEqual(extract_psp_id("NPJH-50001 Monster Hunter"), "NPJH-50001")
        self.assertEqual(extract_psp_id("ULES 00456"), "ULES-00456")

    def test_ps1_id(self):
        self.assertEqual(extract_ps1_id("Код диска: SLUS-00123"), "SLUS-00123")
        self.assertEqual(extract_ps1_id("SLES_001.23"), "SLES-00123")
        self.assertEqual(extract_ps1_id("SCES-00001"), "SCES-00001")
        self.assertEqual(extract_ps1_id("SCUS-94426 Metal Gear Solid"), "SCUS-94426")

    def test_wii_id(self):
        self.assertEqual(extract_wii_id("Код диска: RMCE01"), "RMCE01")
        self.assertEqual(extract_wii_id("Game ID: SB4E01"), "SB4E01")
        self.assertEqual(extract_wii_id("Mario Kart [RMCP01].wbfs"), "RMCP01")

    def test_gamecube_id(self):
        self.assertEqual(extract_gamecube_id("Код диска: GMSE01"), "GMSE01")
        self.assertEqual(extract_gamecube_id("Game ID: GALP01"), "GALP01")

    def test_wiiu_id(self):
        self.assertEqual(extract_wiiu_id("Title ID: 0005000010144F00"), "0005000010144F00")
        self.assertEqual(extract_wiiu_id("Update Title ID: 0005000E10144F00"), "0005000010144F00")
        self.assertEqual(extract_wiiu_id("Product Code: WUP-P-ALZE"), "WUP-P-ALZE")

    def test_retro_id_is_none(self):
        self.assertIsNone(extract_platform_id('nes', "Super Mario Bros. (E) [!]"))
        self.assertIsNone(extract_platform_id('snes', "Chrono Trigger (USA)"))
        self.assertIsNone(extract_platform_id('sega_md', "Sonic The Hedgehog (W) [!]"))


if __name__ == '__main__':
    unittest.main()
