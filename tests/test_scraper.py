import unittest
from unittest.mock import patch, MagicMock
import scraper

class TestScraperSweep(unittest.TestCase):
    @patch('scraper.save_json')
    @patch('scraper.refresh_stale_magnets')
    @patch('scraper.enrich_incomplete')
    @patch('scraper.fetch_atom_feed')
    @patch('scraper.load_json')
    @patch('scraper.get_platform_config')
    @patch('scraper.get_platforms_for_forum')
    def test_update_forum_via_atom_sweep_false(self, mock_get_plats, mock_cfg, mock_load, mock_atom, mock_enrich, mock_refresh, mock_save):
        mock_get_plats.return_value = ['psp']
        mock_cfg.return_value = {'name': 'PSP', 'filename': 'data/psp_games.json', 'strip_tags_re': None}
        mock_load.return_value = []
        mock_atom.return_value = [{'topic_id': '100', 'raw_title': 'Non matching game', 'url': 'http://...'}]

        with patch('scraper.classify_topic', return_value=[]):
            stats = scraper.update_forum_via_atom('1352', target_platforms=['psp'], sweep=False)

        self.assertIn('psp', stats)
        mock_enrich.assert_not_called()
        mock_refresh.assert_not_called()

    @patch('scraper.save_json')
    @patch('scraper.refresh_stale_magnets')
    @patch('scraper.enrich_incomplete')
    @patch('scraper.fetch_atom_feed')
    @patch('scraper.load_json')
    @patch('scraper.get_platform_config')
    @patch('scraper.get_platforms_for_forum')
    def test_update_forum_via_atom_sweep_true(self, mock_get_plats, mock_cfg, mock_load, mock_atom, mock_enrich, mock_refresh, mock_save):
        mock_get_plats.return_value = ['psp']
        mock_cfg.return_value = {'name': 'PSP', 'filename': 'data/psp_games.json', 'strip_tags_re': None}
        mock_load.return_value = []
        mock_atom.return_value = [{'topic_id': '100', 'raw_title': 'Non matching game', 'url': 'http://...'}]
        mock_enrich.return_value = (0, [])
        mock_refresh.return_value = (0, [])

        with patch('scraper.classify_topic', return_value=[]):
            stats = scraper.update_forum_via_atom('1352', target_platforms=['psp'], sweep=True)

        self.assertIn('psp', stats)
        mock_enrich.assert_called_once()
        mock_refresh.assert_called_once()

    def test_cli_sweep_arg(self):
        import argparse
        # Test that parser includes --sweep
        from scraper import main
        # Verify parser configuration
        with patch('argparse.ArgumentParser.parse_args') as mock_parse:
            mock_parse.return_value = argparse.Namespace(
                platform=None, forum=None, full=False, max_pages=None, limit=None, enrich_only=False, sweep=True
            )
            with patch('scraper.run') as mock_run:
                main()
                mock_run.assert_called_once_with(
                    target_platforms=None,
                    target_forums=None,
                    full=False,
                    max_pages=None,
                    enrich_only=False,
                    limit=None,
                    sweep=True
                )

if __name__ == '__main__':
    unittest.main()
