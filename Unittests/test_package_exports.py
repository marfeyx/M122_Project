from __future__ import annotations

import runpy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_DIR = Path(__file__).resolve().parents[1] / "Downloads Folder Sorter"
sys.path.insert(0, str(PROJECT_DIR))

import sorter
from sorter.settings import APP_DIR, CONFIG_PATH, EMAIL_TEMPLATE_PATH


class PackageExportTests(unittest.TestCase):
    def test_sorter_package_exports_public_api(self) -> None:
        self.assertIs(sorter.clean_downloads, sorter.__dict__["clean_downloads"])
        self.assertIn("Config", sorter.__all__)
        self.assertIn("summary_email_html", sorter.__all__)

    def test_settings_paths_are_inside_application_directory(self) -> None:
        self.assertEqual(APP_DIR, PROJECT_DIR)
        self.assertEqual(CONFIG_PATH, PROJECT_DIR / "sorter_config.json")
        self.assertEqual(EMAIL_TEMPLATE_PATH, PROJECT_DIR / "email_template.md")

    def test_download_sorter_launcher_exposes_public_api(self) -> None:
        module = runpy.run_path(str(PROJECT_DIR / "download_sorter.py"), run_name="download_sorter_test")

        self.assertIn("clean_downloads", module)
        self.assertIn("main", module)
        self.assertIn("APP_DIR", module)


if __name__ == "__main__":
    unittest.main()
