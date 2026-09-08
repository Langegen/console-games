"""Тесты извлечения Title ID, Serial и Disc ID."""
import unittest
from core.id_extractors import (
    extract_psp_id,
    extract_ps1_id,
    extract_ps2_id,
    extract_psvita_id,
    extract_dreamcast_id,
    extract_wii_id,
    extract_gamecube_id,
    extract_wiiu_id,
    extract_3ds_id,
    extract_nds_id,
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

    def test_ps2_id(self):
        self.assertEqual(extract_ps2_id("Код диска: SLES-50361"), "SLES-50361")
        self.assertEqual(extract_ps2_id("SLUS_200.02 God of War"), "SLUS-20002")
        self.assertEqual(extract_ps2_id("SCES-51511"), "SCES-51511")
        self.assertEqual(extract_ps2_id("SLPM-65001"), "SLPM-65001")

    def test_psvita_id(self):
        self.assertEqual(extract_psvita_id("Код диска: PCSB-00245"), "PCSB-00245")
        self.assertEqual(extract_psvita_id("PCSE00120 Persona 4 Golden"), "PCSE-00120")
        self.assertEqual(extract_psvita_id("PCSA-00011"), "PCSA-00011")
        self.assertEqual(extract_psvita_id("PCSG-00001"), "PCSG-00001")

    def test_dreamcast_id(self):
        self.assertEqual(extract_dreamcast_id("Код диска: T-13002N"), "T-13002N")
        self.assertEqual(extract_dreamcast_id("Product ID: MK-51000"), "MK-51000")
        self.assertEqual(extract_dreamcast_id("HDR-0014"), "HDR-0014")

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

    def test_3ds_id(self):
        self.assertEqual(extract_3ds_id("Title ID: 00040000000EC400"), "00040000000EC400")
        self.assertEqual(extract_3ds_id("Update Title ID: 0004000E000EC400"), "00040000000EC400")
        self.assertEqual(extract_3ds_id("Product Code: CTR-P-AJEE"), "CTR-P-AJEE")

    def test_nds_id(self):
        self.assertEqual(extract_nds_id("Код игры: NTR-ADAE"), "NTR-ADAE")
        self.assertEqual(extract_nds_id("NTR-P-AMHE"), "NTR-P-AMHE")
        self.assertEqual(extract_nds_id("TWL-P-IRBO"), "TWL-P-IRBO")

    def test_platform_dispatch(self):
        self.assertEqual(extract_platform_id('ps2', "SLUS-20002"), "SLUS-20002")
        self.assertEqual(extract_platform_id('psvita', "PCSB-00245"), "PCSB-00245")
        self.assertEqual(extract_platform_id('dreamcast', "T-13002N"), "T-13002N")
        self.assertEqual(extract_platform_id('3ds', "00040000000EC400"), "00040000000EC400")
        self.assertEqual(extract_platform_id('nds', "NTR-ADAE"), "NTR-ADAE")

    def test_retro_id_is_none(self):
        self.assertIsNone(extract_platform_id('nes', "Super Mario Bros. (E) [!]"))
        self.assertIsNone(extract_platform_id('snes', "Chrono Trigger (USA)"))
        self.assertIsNone(extract_platform_id('sega_md', "Sonic The Hedgehog (W) [!]"))


if __name__ == '__main__':
    unittest.main()
