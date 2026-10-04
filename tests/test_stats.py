"""Тесты для модуля сбора статистики раздач (core/stats.py)."""
import json
import os
import tempfile
import unittest
from unittest.mock import patch

from core.stats import (
    normalize_rutracker_date,
    parse_tracker_page,
    parse_topic_stats,
    scrape_torrents_stats,
    STATS_FILE
)


class TestStatsModule(unittest.TestCase):

    def test_normalize_rutracker_date(self):
        # Русские месяцы
        self.assertEqual(normalize_rutracker_date("15-Сен-24 14:20"), "2024-09-15 14:20:00")
        self.assertEqual(normalize_rutracker_date("01-Янв-25 08:05:30"), "2025-01-01 08:05:30")
        self.assertEqual(normalize_rutracker_date("28-Май-23 23:59"), "2023-05-28 23:59:00")

        # Английские месяцы
        self.assertEqual(normalize_rutracker_date("10-Oct-24 12:30"), "2024-10-10 12:30:00")

        # Уже ISO
        self.assertEqual(normalize_rutracker_date("2024-09-15 14:20:00"), "2024-09-15 14:20:00")

        # Пустые значения
        self.assertIsNone(normalize_rutracker_date(None))
        self.assertIsNone(normalize_rutracker_date(""))

    def test_parse_tracker_page(self):
        sample_html = """
        <table id="tor-tbl">
          <tr id="trs-tr-5001" class="hl-tr">
            <td class="t-title"><a class="tt-text" href="viewtopic.php?t=5001" data-topic_id="5001"><b>God of War [CSO]</b></a></td>
            <td class="seedmed" data-ts_text="25"><b>25</b></td>
            <td class="leechmed" data-ts_text="4">4</td>
            <td class="row4" data-ts_text="8200">8 200</td>
            <td class="row4 small" data-ts_text="1726400000">15-Сен-24 14:20</td>
          </tr>
          <tr id="trs-tr-5002" class="hl-tr">
            <td class="t-title"><a class="tt-text" href="viewtopic.php?t=5002" data-topic_id="5002"><b>Silent Hill [ISO]</b></a></td>
            <td class="seedmed">12</td>
            <td class="leechmed">1</td>
            <td class="row4">3450</td>
            <td class="row4 small">16-Сен-24 10:00</td>
          </tr>
        </table>
        """
        results = parse_tracker_page(sample_html)
        self.assertEqual(len(results), 2)

        self.assertEqual(results[0]["topic_id"], "5001")
        self.assertEqual(results[0]["seeds"], 25)
        self.assertEqual(results[0]["leeches"], 4)
        self.assertEqual(results[0]["downloads"], 8200)
        self.assertEqual(results[0]["registered_at"], "2024-09-15 11:33:20")

        self.assertEqual(results[1]["topic_id"], "5002")
        self.assertEqual(results[1]["seeds"], 12)
        self.assertEqual(results[1]["leeches"], 1)
        self.assertEqual(results[1]["downloads"], 3450)
        self.assertEqual(results[1]["registered_at"], "2024-09-16 10:00:00")

    def test_parse_topic_stats(self):
        sample_html = """
        <table class="attach bordered med">
          <tr><td>Зарегистрирован:</td><td>12-Авг-24 18:45</td></tr>
          <tr><td>Скачан:</td><td><span id="tor-completed">4,120</span> раз</td></tr>
          <tr><td>Сиды:</td><td><span class="seed"><b>31</b></span></td></tr>
          <tr><td>Личи:</td><td><span class="leech"><b>5</b></span></td></tr>
        </table>
        """
        res = parse_topic_stats(sample_html)
        self.assertIsNotNone(res)
        self.assertEqual(res["seeds"], 31)
        self.assertEqual(res["leeches"], 5)
        self.assertEqual(res["downloads"], 4120)
        self.assertEqual(res["registered_at"], "2024-08-12 18:45:00")

    def test_3phase_scrape_stats_multi_platform(self):
        tracker_html = """
        <table id="tor-tbl">
          <tr id="trs-tr-1001" class="hl-tr">
            <td class="t-title"><a data-topic_id="1001" href="viewtopic.php?t=1001"><b>Game 1001</b></a></td>
            <td class="seedmed"><b>50</b></td>
            <td class="leechmed">5</td>
            <td class="row4">1000</td>
            <td class="row4 small">01-Янв-25 10:00</td>
          </tr>
        </table>
        """
        topic_html = """
        <table class="attach bordered med">
          <tr><td>Зарегистрирован:</td><td>02-Фев-25 15:30</td></tr>
          <tr><td>Скачан:</td><td><span id="tor-completed">2,500</span> раз</td></tr>
          <tr><td>Сиды:</td><td><span class="seed"><b>14</b></span></td></tr>
          <tr><td>Личи:</td><td><span class="leech"><b>2</b></span></td></tr>
        </table>
        """

        def mock_fetch(url, *args, **kwargs):
            if "tracker.php" in url:
                return tracker_html
            elif "viewtopic.php" in url:
                return topic_html
            return None

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_stats = os.path.join(tmpdir, "console_games_stats.json")
            tmp_psp = os.path.join(tmpdir, "psp_games.json")

            # База игр: 1001 (будет пойман фазой 1) и 1002 (будет пойман фазой 2)
            games_data = [
                {"topic_id": "1001", "title": "Game 1001"},
                {"topic_id": "1002", "title": "Game 1002"},
            ]
            with open(tmp_psp, 'w', encoding='utf-8') as f:
                json.dump(games_data, f)

            with patch('core.stats.fetch_url', side_effect=mock_fetch):
                with patch('core.stats.get_platform_config', return_value={'filename': tmp_psp, 'forum_id': '1352'}):
                    res = scrape_torrents_stats(
                        output_file=tmp_stats,
                        target_forums=['1352'],
                        target_platforms=['psp'],
                        max_pages=1,
                        full_scan=True
                    )

            self.assertTrue(os.path.exists(tmp_stats))
            with open(tmp_stats, 'r', encoding='utf-8') as f:
                stats = json.load(f)

            self.assertIn("1001", stats)
            self.assertIn("1002", stats)
            self.assertEqual(stats["1001"]["seeds"], 50)
            self.assertEqual(stats["1002"]["seeds"], 14)
            self.assertEqual(stats["1002"]["downloads"], 2500)
            self.assertEqual(stats["1002"]["registered_at"], "2025-02-02 15:30:00")

            self.assertEqual(res["total"], 2)
            self.assertEqual(res["coverage_pct"], 100.0)
            self.assertEqual(res["covered_topics"], 2)
            self.assertEqual(res["target_topics"], 2)


if __name__ == '__main__':
    unittest.main()
