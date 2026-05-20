from __future__ import annotations

import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

PROJECT_DIR = Path(__file__).resolve().parents[1] / "Downloads Folder Sorter"
sys.path.insert(0, str(PROJECT_DIR))

from sorter.config import Config
from sorter.email_summary import (
    markdown_code,
    markdown_inline_to_html,
    markdown_to_html,
    replace_template_variables,
    summary_email_html,
    template_list,
)
from sorter.models import Summary


class EmailSummaryTests(unittest.TestCase):
    def test_template_list_uses_empty_text_for_no_items(self) -> None:
        self.assertEqual(template_list([], "none"), "none")
        self.assertEqual(template_list(["one", "two"], "none"), "- one\n- two")

    def test_markdown_code_removes_backticks(self) -> None:
        self.assertEqual(markdown_code("a`b"), "`ab`")

    def test_replace_template_variables_replaces_known_tokens_only(self) -> None:
        rendered = replace_template_variables("Hello {{name}} {{missing}}", {"name": "Ada"})

        self.assertEqual(rendered, "Hello Ada {{missing}}")

    def test_markdown_inline_to_html_escapes_text_and_renders_inline_markup(self) -> None:
        html = markdown_inline_to_html("**Bold** `<tag>`")

        self.assertEqual(html, "<strong>Bold</strong> <code>&lt;tag&gt;</code>")

    def test_markdown_to_html_renders_headings_lists_and_paragraphs(self) -> None:
        html = markdown_to_html("# Title\n\n## Items\n- one\n- two\n\nText")

        self.assertIn("<h1>Title</h1>", html)
        self.assertIn("<h2>Items</h2>", html)
        self.assertIn("<ul>", html)
        self.assertIn("<li>one</li>", html)
        self.assertIn("<p>Text</p>", html)

    def test_summary_email_html_includes_counts_and_error_status(self) -> None:
        with tempfile.TemporaryDirectory() as root_text:
            template_path = Path(root_text) / "email_template.md"
            template_path.write_text(
                "# {{status}}\n"
                "- Module files moved: {{module_files_moved}}\n"
                "- Errors: {{error_count}}\n"
                "{{module_moves}}\n"
                "{{errors}}\n"
                "{{downloads_path}}\n",
                encoding="utf-8",
            )
            summary = Summary(
                started_at=datetime(2026, 1, 1, 12, 0, 0),
                finished_at=datetime(2026, 1, 1, 12, 0, 2),
                module_files_moved=1,
            )
            summary.module_moves.append(("M122", "source.txt", "dest.txt"))
            summary.errors.append("failed")
            config = Config("Downloads", "Desktop", "Pictures", "Videos")

            with patch("sorter.email_summary.EMAIL_TEMPLATE_PATH", template_path):
                html = summary_email_html(summary, config)

        self.assertIn("<h1>Completed with errors</h1>", html)
        self.assertIn("Module files moved: 1", html)
        self.assertIn("Errors: 1", html)
        self.assertIn("<code>source.txt</code>", html)
        self.assertIn("failed", html)


if __name__ == "__main__":
    unittest.main()
