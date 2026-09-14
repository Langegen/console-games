"""Тесты валидации манифеста эмуляторов data/emulators.json."""

import json
import os
import sys
import unittest

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

from scripts.update_emulators import (
    ALLOWED_CATEGORIES,
    ALLOWED_CONSOLES,
    EMULATOR_DEFINITIONS,
    validate_manifest,
)

EMULATORS_JSON_PATH = os.path.join(ROOT_DIR, "data", "emulators.json")


class TestEmulatorsManifest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.assertTrue(os.path.exists(EMULATORS_JSON_PATH), f"Manifest not found at {EMULATORS_JSON_PATH}")
        with open(EMULATORS_JSON_PATH, "r", encoding="utf-8") as f:
            cls.manifest = json.load(f)

    def test_manifest_is_list(self):
        self.assertIsInstance(self.manifest, list)

    def test_total_emulator_count(self):
        self.assertEqual(len(self.manifest), 17, "Manifest must contain exactly 17 emulator packages")

    def test_validation_passes_cleanly(self):
        errors = validate_manifest(self.manifest)
        self.assertEqual(errors, [], f"Validation errors: {errors}")

    def test_all_20_consoles_covered(self):
        covered = set()
        for emu in self.manifest:
            for cid in emu["supported_console_ids"]:
                covered.add(cid)
        self.assertEqual(covered, ALLOWED_CONSOLES)
        self.assertEqual(len(covered), 20)

    def test_forbidden_consoles_not_present(self):
        forbidden = {"arcade", "pico8", "scummvm"}
        covered = {cid for emu in self.manifest for cid in emu["supported_console_ids"]}
        self.assertTrue(covered.isdisjoint(forbidden), f"Forbidden consoles found: {covered & forbidden}")

    def test_dekopon_requirements(self):
        dekopon = next((e for e in self.manifest if e["id"] == "dekopon"), None)
        self.assertIsNotNone(dekopon)
        self.assertEqual(dekopon["author"], "PalindromicBreadLoaf")
        self.assertIn("3ds", dekopon["supported_console_ids"])
        self.assertEqual(dekopon["category"], "nintendo")
        self.assertEqual(dekopon["install_path"], "sdmc:/switch/dekopon/dekopon.nro")

    def test_nagaa95_ports(self):
        expected = {
            "nethersx2": ("ps2", "sdmc:/switch/NetherSX2/NetherSX2.nro"),
            "dolphin": (["gamecube", "wii"], "sdmc:/switch/dolphin/dolphin.nro"),
            "vita3k": ("psvita", "sdmc:/switch/Vita3K/Vita3K.nro"),
            "cemu": ("wiiu", "sdmc:/switch/cemu/cemu.nro"),
            "drasticds": ("nds", "sdmc:/switch/DrasticDS/DrasticDS.nro"),
        }
        for eid, (expected_platforms, path) in expected.items():
            emu = next((e for e in self.manifest if e["id"] == eid), None)
            self.assertIsNotNone(emu, f"Missing {eid}")
            self.assertEqual(emu["author"], "NaGaa95")
            self.assertEqual(emu["install_path"], path)
            if isinstance(expected_platforms, list):
                for p in expected_platforms:
                    self.assertIn(p, emu["supported_console_ids"])
            else:
                self.assertIn(expected_platforms, emu["supported_console_ids"])

    def test_duckstation_and_ppsspp_archives(self):
        duck = next((e for e in self.manifest if e["id"] == "duckstation"), None)
        self.assertIsNotNone(duck)
        self.assertTrue(duck["is_archive"])
        self.assertEqual(duck["extract_dir"], "sdmc:/switch/duckstation")
        self.assertEqual(duck["install_path"], "sdmc:/switch/duckstation/duckstation.nro")
        self.assertEqual(duck["author"], "shooterspps")

        psp = next((e for e in self.manifest if e["id"] == "ppsspp"), None)
        self.assertIsNotNone(psp)
        self.assertTrue(psp["is_archive"])
        self.assertEqual(psp["extract_dir"], "sdmc:/switch/ppsspp")
        self.assertEqual(psp["install_path"], "sdmc:/switch/ppsspp/PPSSPP_GL.nro")
        self.assertEqual(psp["author"], "SirSamael")

    def test_libretro_cores(self):
        mupen = next((e for e in self.manifest if e["id"] == "mupen64plus_next"), None)
        self.assertIsNotNone(mupen)
        self.assertEqual(mupen["category"], "retroarch")
        self.assertIn("n64", mupen["supported_console_ids"])
        self.assertEqual(mupen["install_path"], "sdmc:/retroarch/cores/mupen64plus_next_libretro_libnx.nro")

        pico = next((e for e in self.manifest if e["id"] == "picodrive"), None)
        self.assertIsNotNone(pico)
        self.assertEqual(pico["category"], "retroarch")
        self.assertIn("sega_32x", pico["supported_console_ids"])
        self.assertEqual(pico["install_path"], "sdmc:/retroarch/cores/picodrive_libretro_libnx.nro")

    def test_categories_and_colors(self):
        for emu in self.manifest:
            self.assertIn(emu["category"], ALLOWED_CATEGORIES)
            self.assertIsInstance(emu["color"], list)
            self.assertEqual(len(emu["color"]), 4)
            for component in emu["color"]:
                self.assertIsInstance(component, int)
                self.assertTrue(0 <= component <= 255)


if __name__ == "__main__":
    unittest.main()
