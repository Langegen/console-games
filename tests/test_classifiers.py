"""Тесты классификации раздач для смешанных разделов f=773 и f=129."""
import unittest
from platforms.classifiers import classify_topic_773, classify_topic_129, classify_topic


class TestClassifiers(unittest.TestCase):

    def test_forum_773_wiiu(self):
        self.assertEqual(classify_topic_773("[Wii U] Super Mario 3D World [WUX]"), ['wiiu'])
        self.assertEqual(classify_topic_773("[WiiU] Xenoblade Chronicles X [Loadiine]"), ['wiiu'])
        self.assertEqual(classify_topic_773("The Legend of Zelda: Breath of the Wild [Wii-U]"), ['wiiu'])

    def test_forum_773_wii(self):
        self.assertEqual(classify_topic_773("[Wii] Super Mario Galaxy [WBFS]"), ['wii'])
        self.assertEqual(classify_topic_773("[Wii] Mario Kart Wii [RUS/ENG]"), ['wii'])
        self.assertEqual(classify_topic_773("Metroid Prime 3: Corruption (Nintendo Wii)"), ['wii'])

    def test_forum_773_gamecube(self):
        self.assertEqual(classify_topic_773("[GameCube] Super Smash Bros. Melee [ISO]"), ['gamecube'])
        self.assertEqual(classify_topic_773("[GC] Resident Evil 4 [NTSC]"), ['gamecube'])
        self.assertEqual(classify_topic_773("[NGC] The Legend of Zelda: The Wind Waker"), ['gamecube'])

    def test_forum_129_nes(self):
        self.assertEqual(classify_topic_129("[NES] Super Mario Bros. [GoodNES]"), ['nes'])
        self.assertEqual(classify_topic_129("[Dendy] Chip and Dale Rescue Rangers [RUS]"), ['nes'])
        self.assertEqual(classify_topic_129("[Famicom] Akumajou Densetsu (Castlevania III)"), ['nes'])

    def test_forum_129_snes(self):
        self.assertEqual(classify_topic_129("[SNES] Chrono Trigger [RUS/ENG]"), ['snes'])
        self.assertEqual(classify_topic_129("[SFC] Final Fantasy VI [JAP]"), ['snes'])
        self.assertEqual(classify_topic_129("Super Metroid [Super Nintendo]"), ['snes'])
        # Убедимся, что SNES не вызывает ложного срабатывания NES
        res = classify_topic_129("[SNES] Donkey Kong Country")
        self.assertIn('snes', res)
        self.assertNotIn('nes', res)

    def test_forum_129_n64(self):
        self.assertEqual(classify_topic_129("[N64] Super Mario 64 [USA]"), ['n64'])
        self.assertEqual(classify_topic_129("[Nintendo 64] The Legend of Zelda: Ocarina of Time"), ['n64'])

    def test_forum_129_gba_and_gbc(self):
        # GBA
        self.assertEqual(classify_topic_129("[GBA] Pokemon Emerald [USA]"), ['gba'])
        self.assertEqual(classify_topic_129("[Game Boy Advance] Castlevania: Aria of Sorrow"), ['gba'])

        # GBC / GB (объединены в gbc_games)
        self.assertEqual(classify_topic_129("[GBC] Pokemon Crystal [RUS]"), ['gbc'])
        self.assertEqual(classify_topic_129("[GB] Tetris [USA]"), ['gbc'])
        self.assertEqual(classify_topic_129("[Game Boy Color] The Legend of Zelda: Oracle of Ages"), ['gbc'])

        # GBA не должен вызывать GBC
        res_gba = classify_topic_129("[GBA] Golden Sun")
        self.assertIn('gba', res_gba)
        self.assertNotIn('gbc', res_gba)

    def test_forum_129_sega_systems(self):
        # SMD / Genesis
        self.assertEqual(classify_topic_129("[SMD] Ultimate Mortal Kombat 3 [RUS]"), ['sega_md'])
        self.assertEqual(classify_topic_129("[Genesis] Sonic The Hedgehog [USA]"), ['sega_md'])
        self.assertEqual(classify_topic_129("[Sega Mega Drive] Streets of Rage 2"), ['sega_md'])

        # Master System
        self.assertEqual(classify_topic_129("[SMS] Alex Kidd in Miracle World"), ['sega_ms'])
        self.assertEqual(classify_topic_129("[Master System] Phantasy Star"), ['sega_ms'])

        # Game Gear
        self.assertEqual(classify_topic_129("[Game Gear] Sonic Triple Trouble"), ['sega_gg'])

        # Sega CD
        self.assertEqual(classify_topic_129("[Sega CD] Sonic CD [ISO]"), ['sega_cd'])

        # 32X
        self.assertEqual(classify_topic_129("[32X] Knuckles' Chaotix"), ['sega_32x'])

    def test_forum_129_multisystem(self):
        # Мультиплатформенный сборник
        res = classify_topic_129("[NES, SNES, Sega] 100 лучших ретро игр 90-х")
        self.assertIn('nes', res)
        self.assertIn('snes', res)
        self.assertIn('sega_md', res)

    def test_universal_classify(self):
        self.assertEqual(classify_topic('1352', "[PSP] God of War: Ghost of Sparta"), ['psp'])
        self.assertEqual(classify_topic('908', "[PS1] Silent Hill [RUS]"), ['ps1'])


if __name__ == '__main__':
    unittest.main()
