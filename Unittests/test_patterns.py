from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1] / "Downloads Folder Sorter"
sys.path.insert(0, str(PROJECT_DIR))

from sorter.patterns import find_modules, is_valid_email, normalize_patterns


class PatternTests(unittest.TestCase):
    def test_find_modules_deduplicates_and_uppercases_matches(self) -> None:
        self.assertEqual(find_modules("m122-M122 notes M450"), ["M122", "M450"])

    def test_find_modules_detects_new_module_codes_without_configuration(self) -> None:
        self.assertEqual(find_modules("Project handout M431 final.pdf"), ["M431"])

    def test_find_modules_requires_module_code_boundaries(self) -> None:
        self.assertEqual(find_modules("SM122 archive M1234 M122_notes.txt"), ["M122"])

    def test_find_modules_only_matches_language_codes_at_start(self) -> None:
        self.assertEqual(find_modules("fr report DE M122 gr"), ["FR", "M122"])

    def test_normalize_patterns_filters_invalid_values_and_sorts(self) -> None:
        patterns = [" m122 ", "invalid", "FR", "m001", "fr", "DE-extra"]

        self.assertEqual(normalize_patterns(patterns), ["FR", "M001", "M122"])

    def test_is_valid_email_requires_complete_address(self) -> None:
        self.assertTrue(is_valid_email(" hello@example.com "))
        self.assertFalse(is_valid_email("hello"))
        self.assertFalse(is_valid_email("hello@example"))


if __name__ == "__main__":
    unittest.main()
