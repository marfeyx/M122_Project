from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

PROJECT_DIR = Path(__file__).resolve().parents[1] / "Downloads Folder Sorter"
sys.path.insert(0, str(PROJECT_DIR))

from sorter.file_ops import (
    extracted_zip_exists,
    move_file,
    record_duplicate_name,
    unique_destination,
)
from sorter.models import Summary


class FileOperationTests(unittest.TestCase):
    def test_unique_destination_adds_counter_before_suffix(self) -> None:
        with tempfile.TemporaryDirectory() as root_text:
            root = Path(root_text)
            destination = root / "report.pdf"
            destination.write_text("existing", encoding="utf-8")
            (root / "report (1).pdf").write_text("existing", encoding="utf-8")

            self.assertEqual(unique_destination(destination), root / "report (2).pdf")

    def test_move_file_creates_destination_and_reports_duplicate(self) -> None:
        with tempfile.TemporaryDirectory() as root_text:
            root = Path(root_text)
            source = root / "source" / "notes.txt"
            destination_folder = root / "destination"
            source.parent.mkdir()
            source.write_text("new", encoding="utf-8")
            destination_folder.mkdir()
            (destination_folder / "notes.txt").write_text("existing", encoding="utf-8")

            result = move_file(source, destination_folder)

            self.assertFalse(source.exists())
            self.assertEqual(result.destination, destination_folder / "notes (1).txt")
            self.assertTrue(result.duplicate_name)
            self.assertEqual(result.destination.read_text(encoding="utf-8"), "new")

    def test_record_duplicate_name_only_records_duplicates(self) -> None:
        summary = Summary()
        with tempfile.TemporaryDirectory() as root_text:
            root = Path(root_text)
            source = root / "a.txt"
            requested = root / "b.txt"
            actual = root / "b (1).txt"

            record_duplicate_name(
                summary,
                source,
                result=type(
                    "Result",
                    (),
                    {
                        "duplicate_name": True,
                        "requested_destination": requested,
                        "destination": actual,
                    },
                )(),
            )

            self.assertEqual(summary.duplicate_name_items, [(str(source), str(requested), str(actual))])

    def test_extracted_zip_exists_checks_same_name_folder_and_archive_roots(self) -> None:
        with tempfile.TemporaryDirectory() as root_text:
            downloads = Path(root_text)
            zip_path = downloads / "archive.zip"
            (downloads / "Extracted").mkdir()
            with ZipFile(zip_path, "w") as archive:
                archive.writestr("Extracted/file.txt", "content")

            self.assertTrue(extracted_zip_exists(zip_path, downloads))
            self.assertFalse(extracted_zip_exists(downloads / "missing.zip", downloads))


if __name__ == "__main__":
    unittest.main()
