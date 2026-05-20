from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1] / "Downloads Folder Sorter"
sys.path.insert(0, str(PROJECT_DIR))

from sorter.config import Config
from sorter.patterns import find_modules
from sorter.sorting import clean_downloads


def test_config(downloads: Path, desktop: Path, images: Path, videos: Path) -> Config:
    return Config(
        downloads_path=str(downloads),
        desktop_path=str(desktop),
        images_path=str(images),
        videos_path=str(videos),
    )


class SortingTests(unittest.TestCase):
    def test_module_matches_keep_filename_order(self) -> None:
        self.assertEqual(find_modules("M122 before M999.txt"), ["M122", "M999"])

    def test_multi_module_file_prefers_existing_desktop_folder(self) -> None:
        with tempfile.TemporaryDirectory() as root_text:
            root = Path(root_text)
            downloads = root / "Downloads"
            desktop = root / "Desktop"
            images = root / "Pictures"
            videos = root / "Videos"
            downloads.mkdir()
            (desktop / "Course M999").mkdir(parents=True)

            source = downloads / "M122 notes M999.pdf"
            source.write_text("content", encoding="utf-8")

            summary = clean_downloads(test_config(downloads, desktop, images, videos))

            self.assertEqual(summary.module_files_moved, 1)
            self.assertEqual(summary.desktop_folders_created, 0)
            self.assertFalse(source.exists())
            self.assertTrue((desktop / "Course M999" / source.name).exists())

    def test_partial_downloads_are_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as root_text:
            root = Path(root_text)
            downloads = root / "Downloads"
            desktop = root / "Desktop"
            images = root / "Pictures"
            videos = root / "Videos"
            downloads.mkdir()

            partial = downloads / "video.mp4.crdownload"
            partial.write_text("still downloading", encoding="utf-8")

            summary = clean_downloads(test_config(downloads, desktop, images, videos))

            self.assertEqual(summary.skipped_files, 1)
            self.assertTrue(partial.exists())
            self.assertIn("partial or temporary download", summary.skipped_items[0][1])

    def test_expanded_media_extensions_are_sorted(self) -> None:
        with tempfile.TemporaryDirectory() as root_text:
            root = Path(root_text)
            downloads = root / "Downloads"
            desktop = root / "Desktop"
            images = root / "Pictures"
            videos = root / "Videos"
            downloads.mkdir()

            image = downloads / "graphic.avif"
            video = downloads / "clip.webm"
            image.write_text("image", encoding="utf-8")
            video.write_text("video", encoding="utf-8")

            summary = clean_downloads(test_config(downloads, desktop, images, videos))

            self.assertEqual(summary.image_files_moved, 1)
            self.assertEqual(summary.video_files_moved, 1)
            self.assertTrue((images / image.name).exists())
            self.assertTrue((videos / video.name).exists())


if __name__ == "__main__":
    unittest.main()
