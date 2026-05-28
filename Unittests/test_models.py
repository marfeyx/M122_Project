from __future__ import annotations

import sys
import unittest
from datetime import datetime
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1] / "Downloads Folder Sorter"
sys.path.insert(0, str(PROJECT_DIR))

from sorter.models import Summary


class ModelTests(unittest.TestCase):
    def test_summary_defaults_create_independent_mutable_lists(self) -> None:
        first = Summary()
        second = Summary()

        first.errors.append("error")

        self.assertIsInstance(first.started_at, datetime)
        self.assertIsNone(first.finished_at)
        self.assertEqual(second.errors, [])


if __name__ == "__main__":
    unittest.main()
