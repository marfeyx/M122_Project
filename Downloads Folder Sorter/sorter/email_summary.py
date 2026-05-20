from __future__ import annotations

import html
import os
import re
from collections.abc import Iterable
from datetime import datetime

from .config import Config
from .models import Summary
from .settings import EMAIL_TEMPLATE_PATH


def template_list(items: Iterable[str], empty_text: str) -> str:
    item_list = list(items)
    if not item_list:
        return empty_text
    return "\n".join("- " + str(item) for item in item_list)


def markdown_code(value: str) -> str:
    return "`" + str(value).replace("`", "") + "`"


def replace_template_variables(template: str, values: dict[str, str]) -> str:
    rendered = template
    for key, value in values.items():
        rendered = rendered.replace(f"{{{{{key}}}}}", value)
    return rendered


def markdown_inline_to_html(markdown_text: str) -> str:
    parts = markdown_text.split("`")
    rendered_parts = []
    for index, part in enumerate(parts):
        escaped = html.escape(part)
        if index % 2 == 1:
            rendered_parts.append(f"<code>{escaped}</code>")
        else:
            rendered_parts.append(re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped))
    return "".join(rendered_parts)


def markdown_to_html(markdown_text: str) -> str:
    html_lines = [
        "<div style=\"font-family: Arial, sans-serif; color: #17202a; line-height: 1.5;\">"
    ]
    in_list = False

    def close_list() -> None:
        nonlocal in_list
        if in_list:
            html_lines.append("</ul>")
            in_list = False

    for raw_line in markdown_text.splitlines():
        stripped = raw_line.rstrip().strip()

        if not stripped:
            close_list()
            continue

        if stripped.startswith("# "):
            close_list()
            html_lines.append(f"<h1>{markdown_inline_to_html(stripped[2:].strip())}</h1>")
        elif stripped.startswith("## "):
            close_list()
            html_lines.append(f"<h2>{markdown_inline_to_html(stripped[3:].strip())}</h2>")
        elif stripped.startswith("### "):
            close_list()
            html_lines.append(f"<h3>{markdown_inline_to_html(stripped[4:].strip())}</h3>")
        elif stripped.startswith("- "):
            if not in_list:
                html_lines.append("<ul>")
                in_list = True
            html_lines.append(f"<li>{markdown_inline_to_html(stripped[2:].strip())}</li>")
        else:
            close_list()
            html_lines.append(f"<p>{markdown_inline_to_html(stripped)}</p>")

    close_list()
    html_lines.append("</div>")
    return "\n".join(html_lines)


def load_email_template() -> str:
    if not EMAIL_TEMPLATE_PATH.exists():
        raise RuntimeError(f"Email template is missing: {EMAIL_TEMPLATE_PATH}")
    return EMAIL_TEMPLATE_PATH.read_text(encoding="utf-8")


def summary_email_html(summary: Summary, config: Config) -> str:
    finished_at = summary.finished_at or datetime.now()
    duration_seconds = round((finished_at - summary.started_at).total_seconds(), 2)
    status = "Completed with errors" if summary.errors else "Completed"

    module_items = [
        f"{module}: {markdown_code(source)} -> {markdown_code(destination)}"
        for module, source, destination in summary.module_moves
    ]
    image_items = [
        f"{markdown_code(source)} -> {markdown_code(destination)}"
        for source, destination in summary.image_moves
    ]
    video_items = [
        f"{markdown_code(source)} -> {markdown_code(destination)}"
        for source, destination in summary.video_moves
    ]
    skipped_items = [
        f"{markdown_code(path)} ({reason})"
        for path, reason in summary.skipped_items
    ]
    duplicate_name_items = [
        (
            f"{markdown_code(source)} could not use existing destination name "
            f"{markdown_code(requested)}; moved as {markdown_code(actual)}"
        )
        for source, requested, actual in summary.duplicate_name_items
    ]

    values = {
        "status": status,
        "finished_at": finished_at.strftime("%Y-%m-%d %H:%M:%S"),
        "duration_seconds": str(duration_seconds),
        "downloads_path": markdown_code(config.downloads_path),
        "desktop_path": markdown_code(config.desktop_path),
        "images_path": markdown_code(config.images_path),
        "videos_path": markdown_code(config.videos_path),
        "module_files_moved": str(summary.module_files_moved),
        "image_files_moved": str(summary.image_files_moved),
        "video_files_moved": str(summary.video_files_moved),
        "desktop_folders_created": str(summary.desktop_folders_created),
        "zip_files_deleted": str(summary.zip_files_deleted),
        "skipped_files": str(summary.skipped_files),
        "unassigned_module_files": str(summary.unassigned_module_files),
        "error_count": str(len(summary.errors)),
        "duplicate_name_count": str(len(summary.duplicate_name_items)),
        "module_moves": template_list(module_items, "No Module files were moved."),
        "image_moves": template_list(image_items, "No images were moved."),
        "video_moves": template_list(video_items, "No videos were moved."),
        "created_folders": template_list(
            (markdown_code(path) for path in summary.created_folders),
            "No desktop folders were created.",
        ),
        "deleted_zips": template_list(
            (markdown_code(path) for path in summary.deleted_zips),
            "No .zip files were deleted.",
        ),
        "duplicate_name_items": template_list(
            duplicate_name_items,
            "No duplicate file names were encountered.",
        ),
        "skipped_items": template_list(skipped_items, "No files were skipped."),
        "unassigned_module_items": template_list(
            (markdown_code(path) for path in summary.unassigned_module_items),
            "No files were left without an MXXX module assignment.",
        ),
        "errors": template_list(summary.errors, "No errors occurred."),
    }

    return markdown_to_html(replace_template_variables(load_email_template(), values))


def send_summary_email(summary: Summary, config: Config) -> None:
    try:
        import resend
    except ImportError as error:
        raise RuntimeError(
            "The 'resend' package is missing. Install it with: pip install resend"
        ) from error

    api_key = config.resend_api_key.strip() or os.environ.get("RESEND_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("No Resend API key is configured.")

    resend.api_key = api_key
    resend.Emails.send(
        {
            "from": config.email_from,
            "to": config.email_to,
            "subject": "Downloads Sorter detailed summary",
            "html": summary_email_html(summary, config),
        }
    )
