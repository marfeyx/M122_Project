from __future__ import annotations

import shutil
from datetime import datetime, timedelta
from pathlib import Path

from .config import Config
from .file_ops import extracted_zip_exists, move_file, record_duplicate_name
from .models import Summary
from .paths import is_inside, resolve_path
from .patterns import find_modules, normalize_patterns

IMAGE_EXTENSIONS = {
    ".apng",
    ".avif",
    ".bmp",
    ".gif",
    ".heic",
    ".heif",
    ".ico",
    ".jfif",
    ".jpeg",
    ".jpg",
    ".png",
    ".svg",
    ".tif",
    ".tiff",
    ".webp",
}

VIDEO_EXTENSIONS = {
    ".3gp",
    ".avi",
    ".flv",
    ".m4v",
    ".mkv",
    ".mov",
    ".mp4",
    ".mpeg",
    ".mpg",
    ".webm",
    ".wmv",
}

PARTIAL_DOWNLOAD_EXTENSIONS = {
    ".crdownload",
    ".download",
    ".part",
    ".partial",
    ".tmp",
}

IGNORED_FILE_NAMES = {"desktop.ini", "thumbs.db"}


def exclusion_reason(path: Path, modules: list[str], config: Config) -> str | None:
    resolved = path.resolve()

    for excluded in config.excluded_paths:
        excluded_path = resolve_path(excluded)
        if resolved == excluded_path or is_inside(resolved, excluded_path):
            return f"excluded path/file: {excluded_path}"

    if path.is_file():
        suffix = path.suffix.lower()
        if path.name.lower() in IGNORED_FILE_NAMES:
            return "system file"
        if suffix in PARTIAL_DOWNLOAD_EXTENSIONS:
            return "partial or temporary download"

    if config.exclude_newer_than_days is not None:
        newest_allowed_time = datetime.now() - timedelta(days=config.exclude_newer_than_days)
        modified_time = datetime.fromtimestamp(path.stat().st_mtime)
        if modified_time > newest_allowed_time:
            return f"newer than {config.exclude_newer_than_days} day(s)"

    excluded_modules = set(normalize_patterns(config.excluded_patterns))
    matching_modules = excluded_modules.intersection(modules)
    if matching_modules:
        return f"excluded pattern: {', '.join(sorted(matching_modules))}"

    return None


def is_excluded(path: Path, modules: list[str], config: Config) -> bool:
    return exclusion_reason(path, modules, config) is not None


def desktop_module_folders(desktop_path: Path) -> dict[str, Path]:
    folders: dict[str, Path] = {}
    if not desktop_path.exists():
        desktop_path.mkdir(parents=True, exist_ok=True)

    for item in desktop_path.iterdir():
        if not item.is_dir():
            continue
        for module in find_modules(item.name):
            folders.setdefault(module, item)
    return folders


def choose_module_folder(
    modules: list[str],
    desktop_path: Path,
    desktop_folders: dict[str, Path],
) -> tuple[str, Path, bool]:
    for module in modules:
        existing_folder = desktop_folders.get(module)
        if existing_folder is not None:
            return module, existing_folder, False

    module = modules[0]
    destination_folder = desktop_path / module
    destination_folder.mkdir(parents=True, exist_ok=True)
    desktop_folders[module] = destination_folder
    return module, destination_folder, True


def delete_extracted_zips(downloads_path: Path, config: Config, summary: Summary) -> None:
    for zip_path in downloads_path.glob("*.zip"):
        if not zip_path.is_file():
            continue

        modules = find_modules(zip_path.name)
        try:
            reason = exclusion_reason(zip_path, modules, config)
            if reason is not None:
                summary.skipped_files += 1
                summary.skipped_items.append((str(zip_path), reason))
                continue
            if extracted_zip_exists(zip_path, downloads_path):
                zip_path.unlink()
                summary.zip_files_deleted += 1
                summary.deleted_zips.append(str(zip_path))
        except OSError as error:
            summary.errors.append(f"Could not process zip '{zip_path}': {error}")


def clean_downloads(config: Config) -> Summary:
    summary = Summary()
    downloads_path = resolve_path(config.downloads_path)
    desktop_path = resolve_path(config.desktop_path)
    images_path = resolve_path(config.images_path)
    videos_path = resolve_path(config.videos_path)

    if not downloads_path.exists():
        summary.errors.append(f"Downloads folder does not exist: {downloads_path}")
        summary.finished_at = datetime.now()
        return summary

    desktop_folders = desktop_module_folders(desktop_path)
    delete_extracted_zips(downloads_path, config, summary)

    for item in sorted(downloads_path.iterdir(), key=lambda path: path.name.lower()):
        is_file = item.is_file()
        is_directory = item.is_dir()
        if not is_file and not is_directory:
            continue

        modules = find_modules(item.name)
        try:
            reason = exclusion_reason(item, modules, config)
            if reason is not None:
                summary.skipped_files += 1
                summary.skipped_items.append((str(item), reason))
                continue

            if modules:
                module, destination_folder, folder_created = choose_module_folder(
                    modules,
                    desktop_path,
                    desktop_folders,
                )
                if folder_created:
                    summary.desktop_folders_created += 1
                    summary.created_folders.append(str(destination_folder))

                move_result = move_file(item, destination_folder)
                record_duplicate_name(summary, item, move_result)
                summary.module_files_moved += 1
                summary.module_moves.append((module, str(item), str(move_result.destination)))
                continue

            if is_file and item.suffix.lower() in IMAGE_EXTENSIONS:
                move_result = move_file(item, images_path)
                record_duplicate_name(summary, item, move_result)
                summary.image_files_moved += 1
                summary.image_moves.append((str(item), str(move_result.destination)))
                continue

            if is_file and item.suffix.lower() in VIDEO_EXTENSIONS:
                move_result = move_file(item, videos_path)
                record_duplicate_name(summary, item, move_result)
                summary.video_files_moved += 1
                summary.video_moves.append((str(item), str(move_result.destination)))
                continue

            if is_file:
                summary.unassigned_module_files += 1
                summary.unassigned_module_items.append(str(item))
        except (OSError, shutil.Error) as error:
            summary.errors.append(f"Could not process item '{item}': {error}")

    summary.finished_at = datetime.now()
    return summary
