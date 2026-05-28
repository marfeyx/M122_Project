from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_DIR = Path(__file__).resolve().parents[1] / "Downloads Folder Sorter"
sys.path.insert(0, str(PROJECT_DIR))

from sorter.paths import expand_environment_variables, is_inside, known_folder_path, resolve_path


class PathTests(unittest.TestCase):
    def test_resolve_path_expands_user_and_environment_variables(self) -> None:
        with tempfile.TemporaryDirectory() as root_text:
            root = Path(root_text)
            os.environ["SORTER_TEST_ROOT"] = str(root)

            self.assertEqual(resolve_path("%SORTER_TEST_ROOT%"), root.resolve())

    def test_expand_environment_variables_keeps_unknown_windows_variables(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(
                expand_environment_variables("%MISSING_VAR%/file"),
                "%MISSING_VAR%/file",
            )

    def test_is_inside_detects_nested_paths(self) -> None:
        with tempfile.TemporaryDirectory() as root_text:
            root = Path(root_text)
            child = root / "nested" / "file.txt"

            self.assertTrue(is_inside(child, root))
            self.assertFalse(is_inside(root, child))

    def test_known_folder_path_uses_fallback_outside_windows(self) -> None:
        fallback = Path("fallback")

        with patch("sorter.paths.os.name", "posix"):
            self.assertEqual(known_folder_path("downloads", fallback), fallback)


if __name__ == "__main__":
    unittest.main()
