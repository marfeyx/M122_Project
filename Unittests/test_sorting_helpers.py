from __future__ import annotations

import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from zipfile import ZipFile
from unittest.mock import patch

PROJECT_DIR = Path(__file__).resolve().parents[1] / "Downloads Folder Sorter"
sys.path.insert(0, str(PROJECT_DIR))

from sorter.config import Config
from sorter.models import Summary
from sorter.sorting import (
    choose_module_folder,
    delete_extracted_zips,
    desktop_module_folders,
    exclusion_reason,
    is_excluded,
)


def test_config(downloads: Path, desktop: Path, images: Path, videos: Path) -> Config:
    return Config(
        downloads_path=str(downloads),
        desktop_path=str(desktop),
        images_path=str(images),
        videos_path=str(videos),
    )


class SortingHelperTests(unittest.TestCase):
    def test_exclusion_reason_handles_excluded_path_pattern_and_new_files(self) -> None:
        with tempfile.TemporaryDirectory() as root_text:
            root = Path(root_text)
            downloads = root / "Downloads"
            desktop = root / "Desktop"
            images = root / "Pictures"
            videos = root / "Videos"
            downloads.mkdir()
            excluded = downloads / "skip.txt"
            excluded.write_text("skip", encoding="utf-8")
            config = test_config(downloads, desktop, images, videos)
            config.excluded_paths = [str(excluded)]

            self.assertIn("excluded path/file", exclusion_reason(excluded, [], config))

            config.excluded_paths = []
            config.excluded_patterns = ["M122"]
            self.assertEqual(exclusion_reason(downloads / "M122 notes.txt", ["M122"], config), "excluded pattern: M122")

            config.excluded_patterns = []
            config.exclude_newer_than_days = 1
            recent = downloads / "recent.txt"
            recent.write_text("recent", encoding="utf-8")
            self.assertEqual(exclusion_reason(recent, [], config), "newer than 1 day(s)")

    def test_is_excluded_returns_boolean_from_exclusion_reason(self) -> None:
        with tempfile.TemporaryDirectory() as root_text:
            root = Path(root_text)
            file_path = root / "desktop.ini"
            file_path.write_text("", encoding="utf-8")
            config = Config(str(root), str(root), str(root), str(root))

            self.assertTrue(is_excluded(file_path, [], config))
            self.assertFalse(is_excluded(root / "notes.txt", [], config))

    def test_desktop_module_folders_creates_desktop_and_indexes_matches(self) -> None:
        with tempfile.TemporaryDirectory() as root_text:
            desktop = Path(root_text) / "Desktop"

            folders = desktop_module_folders(desktop)
            self.assertEqual(folders, {})
            self.assertTrue(desktop.exists())

            (desktop / "Course M122").mkdir()
            folders = desktop_module_folders(desktop)

            self.assertEqual(folders["M122"], desktop / "Course M122")

    def test_choose_module_folder_prefers_existing_then_creates_first_module(self) -> None:
        with tempfile.TemporaryDirectory() as root_text:
            desktop = Path(root_text)
            existing = desktop / "Existing M999"
            existing.mkdir()
            folders = {"M999": existing}

            self.assertEqual(choose_module_folder(["M122", "M999"], desktop, folders), ("M999", existing, False))

            module, folder, created = choose_module_folder(["M122"], desktop, folders)

            self.assertEqual((module, folder, created), ("M122", desktop / "M122", True))
            self.assertTrue(folder.exists())

    def test_delete_extracted_zips_removes_only_matching_extracted_archives(self) -> None:
        with tempfile.TemporaryDirectory() as root_text:
            downloads = Path(root_text)
            extracted = downloads / "archive"
            extracted.mkdir()
            zip_path = downloads / "archive.zip"
            other_zip = downloads / "other.zip"
            with ZipFile(zip_path, "w") as archive:
                archive.writestr("archive/file.txt", "content")
            with ZipFile(other_zip, "w") as archive:
                archive.writestr("other/file.txt", "content")
            summary = Summary()
            config = Config(str(downloads), str(downloads), str(downloads), str(downloads))

            delete_extracted_zips(downloads, config, summary)

            self.assertFalse(zip_path.exists())
            self.assertTrue(other_zip.exists())
            self.assertEqual(summary.zip_files_deleted, 1)

    def test_desktop_module_folders_ignores_files(self) -> None:
        with tempfile.TemporaryDirectory() as root_text:
            desktop = Path(root_text)
            (desktop / "M122 file.txt").write_text("not a folder", encoding="utf-8")

            self.assertEqual(desktop_module_folders(desktop), {})

    def test_delete_extracted_zips_skips_excluded_archives_and_records_errors(self) -> None:
        with tempfile.TemporaryDirectory() as root_text:
            downloads = Path(root_text)
            skipped_zip = downloads / "skip.zip"
            error_zip = downloads / "error.zip"
            skipped_zip.write_text("skip", encoding="utf-8")
            error_zip.write_text("error", encoding="utf-8")
            summary = Summary()
            config = Config(str(downloads), str(downloads), str(downloads), str(downloads))
            config.excluded_paths = [str(skipped_zip)]

            with patch("sorter.sorting.extracted_zip_exists", side_effect=OSError("broken zip")):
                delete_extracted_zips(downloads, config, summary)

            self.assertEqual(summary.skipped_files, 1)
            self.assertIn("excluded path/file", summary.skipped_items[0][1])
            self.assertEqual(len(summary.errors), 1)
            self.assertIn("Could not process zip", summary.errors[0])


if __name__ == "__main__":
    unittest.main()
