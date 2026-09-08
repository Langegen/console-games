"""Тесты парсера постов, magnet-ссылок и очистки заголовков."""
import unittest
from core.topic_parser import clean_magnet, clean_title, parse_feed_title
from platforms.configs import PLATFORM_CONFIGS


class TestTopicParser(unittest.TestCase):

    def test_clean_magnet(self):
        raw = "magnet:?xt=urn:btih:12345ABCDE&amp;dn=Sample+Game&tr=http%3A%2F%2Fbt.org"
        cleaned = clean_magnet(raw)
        self.assertNotIn('&amp;', cleaned)
        self.assertNotIn('dn=', cleaned)
        self.assertIn('xt=urn:btih:12345ABCDE', cleaned)

    def test_clean_title(self):
        psp_re = PLATFORM_CONFIGS['psp']['strip_tags_re']
        self.assertEqual(clean_title("[PSP] God of War: Ghost of Sparta [EUR]", psp_re), "God of War: Ghost of Sparta [EUR]")

        wiiu_re = PLATFORM_CONFIGS['wiiu']['strip_tags_re']
        self.assertEqual(clean_title("[Wii U] Bayonetta 2 [RUS/ENG]", wiiu_re), "Bayonetta 2 [RUS/ENG]")

        nes_re = PLATFORM_CONFIGS['nes']['strip_tags_re']
        self.assertEqual(clean_title("[NES] Battle City [RUS]", nes_re), "Battle City [RUS]")

        ps2_re = PLATFORM_CONFIGS['ps2']['strip_tags_re']
        self.assertEqual(clean_title("[PS2] Shadow of the Colossus [RUS]", ps2_re), "Shadow of the Colossus [RUS]")

        vita_re = PLATFORM_CONFIGS['psvita']['strip_tags_re']
        self.assertEqual(clean_title("[PSV] Persona 4 Golden [ENG]", vita_re), "Persona 4 Golden [ENG]")

        dc_re = PLATFORM_CONFIGS['dreamcast']['strip_tags_re']
        self.assertEqual(clean_title("[DC] Sonic Adventure [ENG]", dc_re), "Sonic Adventure [ENG]")

        n3ds_re = PLATFORM_CONFIGS['3ds']['strip_tags_re']
        self.assertEqual(clean_title("[3DS] Pokemon X [EUR]", n3ds_re), "Pokemon X [EUR]")

        nds_re = PLATFORM_CONFIGS['nds']['strip_tags_re']
        self.assertEqual(clean_title("[NDS] Pokemon Platinum [USA]", nds_re), "Pokemon Platinum [USA]")

    def test_parse_feed_title(self):
        psp_re = PLATFORM_CONFIGS['psp']['strip_tags_re']
        raw = "[PSP] Tekken 6 [EUR] [850.5 MB]"
        title, size = parse_feed_title(raw, psp_re)
        self.assertEqual(size, "850.5 MB")
        self.assertEqual(title, "Tekken 6 [EUR]")


if __name__ == '__main__':
    unittest.main()
