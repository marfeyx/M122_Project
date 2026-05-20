from __future__ import annotations
import ctypes
import html
import importlib.util
import json
import os
import re
import shutil
import site
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable
from zipfile import BadZipFile, ZipFile


APP_DIR = Path(__file__).resolve().parent
CONFIG_PATH = APP_DIR / "sorter_config.json"
EMAIL_TEMPLATE_PATH = APP_DIR / "email_template.md"
MODULE_PATTERN = re.compile(r"M\d{3}|^(?:DE|GR|FR|PH)(?=$|[\s_.-])", re.IGNORECASE)
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".bmp",
    ".tif",
    ".tiff",
    ".webp",
    ".heic",
    ".heif",
    ".svg",
    ".ico",
}

VIDEO_EXTENSIONS = {
    ".mp4",
    ".mov",
    ".avi",
    ".mkv",
}

KNOWN_FOLDER_IDS = {
    "downloads": "{374DE290-123F-4565-9164-39C4925E467B}",
    "desktop": "{B4BFCC3A-DB2C-424C-B029-7FE99A87C641}",
    "pictures": "{33E28130-4E1E-4676-835A-98395C3BC3BB}",
    "videos": "{18989B1D-99B5-455B-841C-AB7C74E4DDFC}",
}

@dataclass
class Config:
    downloads_path: str
    desktop_path: str
    images_path: str
    videos_path: str
    resend_api_key: str = ""
    email_from: str = "onboarding@resend.dev"
    email_to: str = "recipient@example.com"
    excluded_paths: list[str] = field(default_factory=list)
    exclude_newer_than_days: int | None = None
    excluded_patterns: list[str] = field(default_factory=list)

    @classmethod
    def load(cls) -> "Config":
        # Start with OS-specific default folders so the program still works even if the config file is missing.
        defaults = default_config()
        if not CONFIG_PATH.exists():
            # Create the file on first run so the user has something they can edit later.
            defaults.save()
            return defaults

        try:
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            # If the file is broken or unreadable, fall back to safe defaults instead of crashing.
            print("Config file could not be read. Default settings will be used.")
            return defaults

        # Keep user-provided email addresses only when they still look valid.
        email_from = data.get("email_from") or defaults.email_from
        email_to = data.get("email_to") or defaults.email_to

        return cls(
            downloads_path=data.get("downloads_path") or defaults.downloads_path,
            desktop_path=data.get("desktop_path") or defaults.desktop_path,
            images_path=data.get("images_path") or defaults.images_path,
            videos_path=data.get("videos_path") or defaults.videos_path,
            resend_api_key=data.get("resend_api_key") or "",
            email_from=email_from if is_valid_email(email_from) else defaults.email_from,
            email_to=email_to if is_valid_email(email_to) else defaults.email_to,
            excluded_paths=list(data.get("excluded_paths") or []),
            exclude_newer_than_days=data.get("exclude_newer_than_days"),
            excluded_patterns=normalize_patterns(data.get("excluded_patterns") or []),
        )

    def save(self) -> None:
        CONFIG_PATH.write_text(
            json.dumps(self.__dict__, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )


@dataclass
class Summary:
    started_at: datetime = field(default_factory=datetime.now)
    finished_at: datetime | None = None
    module_files_moved: int = 0
    image_files_moved: int = 0
    video_files_moved: int = 0
    desktop_folders_created: int = 0
    zip_files_deleted: int = 0
    skipped_files: int = 0
    unassigned_module_files: int = 0
    module_moves: list[tuple[str, str, str]] = field(default_factory=list)
    image_moves: list[tuple[str, str]] = field(default_factory=list)
    video_moves: list[tuple[str, str]] = field(default_factory=list)
    created_folders: list[str] = field(default_factory=list)
    deleted_zips: list[str] = field(default_factory=list)
    skipped_items: list[tuple[str, str]] = field(default_factory=list)
    unassigned_module_items: list[str] = field(default_factory=list)
    duplicate_name_items: list[tuple[str, str, str]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass
class MoveResult:
    destination: Path
    duplicate_name: bool
    requested_destination: Path


def known_folder_path(folder_name: str, fallback: Path) -> Path:
    if os.name != "nt":
        return fallback

    folder_id = KNOWN_FOLDER_IDS[folder_name]

    class GUID(ctypes.Structure):
        _fields_ = [
            ("Data1", ctypes.c_ulong),
            ("Data2", ctypes.c_ushort),
            ("Data3", ctypes.c_ushort),
            ("Data4", ctypes.c_ubyte * 8),
        ]

    shell32 = ctypes.windll.shell32
    ole32 = ctypes.windll.ole32
    guid = GUID()
    path_pointer = ctypes.c_void_p()

    if ole32.CLSIDFromString(folder_id, ctypes.byref(guid)) != 0:
        return fallback

    result = shell32.SHGetKnownFolderPath(
        ctypes.byref(guid),
        0,
        None,
        ctypes.byref(path_pointer),
    )
    if result != 0:
        return fallback

    try:
        return Path(ctypes.wstring_at(path_pointer.value))
    finally:
        ole32.CoTaskMemFree(path_pointer)


def default_config() -> Config:
    # On Windows we try the known shell folders first; on other systems we use the home directory fallbacks.
    home = Path.home()
    return Config(
        downloads_path=str(known_folder_path("downloads", home / "Downloads")),
        desktop_path=str(known_folder_path("desktop", home / "Desktop")),
        images_path=str(known_folder_path("pictures", home / "Pictures")),
        videos_path=str(known_folder_path("videos", home / "Videos")),
    )


def normalize_patterns(patterns: Iterable[str]) -> list[str]:
    normalized = []
    for pattern in patterns:
        # Accept user input like "m123" or "M123" but store it in a consistent format.
        pattern_as_text = str(pattern)
        pattern_as_text = pattern_as_text.strip()
        match = MODULE_PATTERN.fullmatch(pattern_as_text)
        if match is not None:
            module_name = match.group(0)
            module_name = module_name.upper()
            if module_name not in normalized:
                normalized.append(module_name)
    normalized.sort()
    return normalized


def find_modules(text: str) -> list[str]:
    modules = []
    matches = MODULE_PATTERN.finditer(text)
    for match in matches:
        # A filename can contain several module codes, so we collect them all before sorting.
        module_name = match.group(0)
        module_name = module_name.upper()
        if module_name not in modules:
            modules.append(module_name)
    modules.sort()
    return modules


def resolve_path(path_text: str) -> Path:
    # Expand things like %USERPROFILE% and ~ before turning the text into an absolute path.
    return Path(os.path.expandvars(os.path.expanduser(path_text))).resolve()


def is_inside(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        # relative_to raises ValueError when the child is not inside the parent folder.
        return False


def is_excluded(path: Path, modules: list[str], config: Config) -> bool:
    return exclusion_reason(path, modules, config) is not None


def exclusion_reason(path: Path, modules: list[str], config: Config) -> str | None:
    resolved = path.resolve()

    # Explicit path exclusions take priority over the other rules.
    for excluded in config.excluded_paths:
        excluded_path = resolve_path(excluded)
        if resolved == excluded_path or is_inside(resolved, excluded_path):
            return f"excluded path/file: {excluded_path}"

    # Skip files that are too new before checking module-based exclusions.
    if config.exclude_newer_than_days is not None:
        newest_allowed_time = datetime.now() - timedelta(days=config.exclude_newer_than_days)
        modified_time = datetime.fromtimestamp(path.stat().st_mtime)
        if modified_time > newest_allowed_time:
            return f"newer than {config.exclude_newer_than_days} day(s)"

    # Module pattern exclusions are evaluated last so they only apply to files that survive the other filters.
    excluded_modules = set(normalize_patterns(config.excluded_patterns))
    matching_modules = excluded_modules.intersection(modules)
    if matching_modules:
        return f"excluded pattern: {', '.join(sorted(matching_modules))}"

    return None


def desktop_module_folders(desktop_path: Path) -> dict[str, Path]:
    folders: dict[str, Path] = {}
    if not desktop_path.exists():
        # Make sure the desktop folder exists before we scan it.
        desktop_path.mkdir(parents=True, exist_ok=True)

    for item in desktop_path.iterdir():
        if not item.is_dir():
            continue
        for module in find_modules(item.name):
            folders.setdefault(module, item)
    return folders


def unique_destination(destination: Path) -> Path:
    destination_exists = destination.exists()
    if destination_exists == False:
        return destination

    # If a file with the same name already exists, append "(1)", "(2)", and so on.
    counter = 1
    while True:
        file_stem = destination.stem
        file_suffix = destination.suffix
        new_name = file_stem + " (" + str(counter) + ")" + file_suffix
        candidate = destination.with_name(new_name)
        candidate_exists = candidate.exists()
        if candidate_exists == False:
            return candidate
        counter = counter + 1


def move_file(source: Path, destination_folder: Path) -> MoveResult:
    # Create the target folder if needed so shutil.move has a valid destination.
    destination_folder.mkdir(parents=True, exist_ok=True)
    requested_destination = destination_folder / source.name
    destination = unique_destination(requested_destination)
    shutil.move(str(source), str(destination))
    return MoveResult(
        destination=destination,
        duplicate_name=destination != requested_destination,
        requested_destination=requested_destination,
    )


def record_duplicate_name(summary: Summary, source: Path, result: MoveResult) -> None:
    if result.duplicate_name:
        summary.duplicate_name_items.append(
            (
                str(source),
                str(result.requested_destination),
                str(result.destination),
            )
        )


def extracted_zip_exists(zip_path: Path, downloads_path: Path) -> bool:
    # Some archives extract into a folder with the zip's stem, others expose a top-level folder from inside the archive.
    same_name_folder = downloads_path / zip_path.stem
    if same_name_folder.is_dir():
        return True

    try:
        with ZipFile(zip_path) as archive:
            top_level_names = {
                Path(name).parts[0]
                for name in archive.namelist()
                if name.strip("/") and Path(name).parts
            }
    except (BadZipFile, OSError):
        return False

    for top_level_name in top_level_names:
        candidate = downloads_path / top_level_name
        if candidate.is_dir():
            return True

    return False


def delete_extracted_zips(downloads_path: Path, config: Config, summary: Summary) -> None:
    for zip_path in downloads_path.glob("*.zip"):
        if not zip_path.is_file():
            continue

        modules = find_modules(zip_path.name)
        try:
            reason = exclusion_reason(zip_path, modules, config)
            if reason is not None:
                # Excluded items are tracked separately so the summary can explain why they were ignored.
                summary.skipped_files += 1
                summary.skipped_items.append((str(zip_path), reason))
                continue
            if extracted_zip_exists(zip_path, downloads_path):
                # Remove the archive only after we confirm the extracted folder already exists.
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
        # Stop early when the main input folder does not exist, because nothing else can work without it.
        summary.errors.append(f"Downloads folder does not exist: {downloads_path}")
        summary.finished_at = datetime.now()
        return summary

    desktop_folders = desktop_module_folders(desktop_path)
    # Clean up extracted archives first so later moves do not leave stale zip files behind.
    delete_extracted_zips(downloads_path, config, summary)

    for item in list(downloads_path.iterdir()):
        is_file = item.is_file()
        is_directory = item.is_dir()
        if not is_file and not is_directory:
            continue

        modules = find_modules(item.name)
        try:
            reason = exclusion_reason(item, modules, config)
            if reason is not None:
                # Once a file matches an exclusion rule, we leave it untouched.
                summary.skipped_files += 1
                summary.skipped_items.append((str(item), reason))
                continue

            if modules:
                # Module files are routed to desktop folders named after the module code.
                module = modules[0]
                destination_folder = desktop_folders.get(module)
                if destination_folder is None:
                    destination_folder = desktop_path / module
                    destination_folder.mkdir(parents=True, exist_ok=True)
                    desktop_folders[module] = destination_folder
                    summary.desktop_folders_created += 1
                    summary.created_folders.append(str(destination_folder))
                move_result = move_file(item, destination_folder)
                record_duplicate_name(summary, item, move_result)
                summary.module_files_moved += 1
                summary.module_moves.append((module, str(item), str(move_result.destination)))
                continue

            if is_file and item.suffix.lower() in IMAGE_EXTENSIONS:
                # Plain images go to the dedicated images folder.
                move_result = move_file(item, images_path)
                record_duplicate_name(summary, item, move_result)
                summary.image_files_moved += 1
                summary.image_moves.append((str(item), str(move_result.destination)))
                continue

            if is_file and item.suffix.lower() in VIDEO_EXTENSIONS:
                # Plain videos go to the dedicated videos folder.
                move_result = move_file(item, videos_path)
                record_duplicate_name(summary, item, move_result)
                summary.video_files_moved += 1
                summary.video_moves.append((str(item), str(move_result.destination)))
                continue

            if is_file:
                # Files that do not match any rule are left in Downloads and reported in the summary.
                summary.unassigned_module_files += 1
                summary.unassigned_module_items.append(str(item))
        except (OSError, shutil.Error) as error:
            # File operations can still fail because of permissions, locked files, or bad paths.
            summary.errors.append(f"Could not process item '{item}': {error}")

    summary.finished_at = datetime.now()
    return summary


def template_list(items: Iterable[str], empty_text: str) -> str:
    item_list = list(items)
    if len(item_list) == 0:
        return empty_text
    lines = []
    for item in item_list:
        # The email template expects markdown bullets, so each line is prefixed with "- ".
        line = "- " + str(item)
        lines.append(line)
    final_text = "\n".join(lines)
    return final_text


def markdown_code(value: str) -> str:
    text = str(value)
    text = text.replace("`", "")
    text = "`" + text + "`"
    return text


def replace_template_variables(template: str, values: dict[str, str]) -> str:
    rendered = template
    for key, value in values.items():
        rendered = rendered.replace(f"{{{{{key}}}}}", value)
    return rendered


def markdown_inline_to_html(markdown_text: str) -> str:
    # This is a small custom renderer that supports just the markdown features used by the template.
    parts = markdown_text.split("`")
    rendered_parts = []
    for index, part in enumerate(parts):
        escaped = html.escape(part)
        if index % 2 == 1:
            rendered_parts.append(f"<code>{escaped}</code>")
        else:
            escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)
            rendered_parts.append(escaped)
    return "".join(rendered_parts)


def markdown_to_html(markdown_text: str) -> str:
    # Build a simple HTML document line by line so the email stays readable in common mail clients.
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
        line = raw_line.rstrip()
        stripped = line.strip()

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
    status = "Completed"
    if summary.errors:
        status = "Completed with errors"

    # Convert the collected move and skip records into simple markdown list items for the template.
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
    unassigned_module_items = [
        markdown_code(path)
        for path in summary.unassigned_module_items
    ]
    created_folders = [markdown_code(path) for path in summary.created_folders]
    deleted_zips = [markdown_code(path) for path in summary.deleted_zips]
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
        "created_folders": template_list(created_folders, "No desktop folders were created."),
        "deleted_zips": template_list(deleted_zips, "No .zip files were deleted."),
        "duplicate_name_items": template_list(
            duplicate_name_items,
            "No duplicate file names were encountered.",
        ),
        "skipped_items": template_list(skipped_items, "No files were skipped."),
        "unassigned_module_items": template_list(
            unassigned_module_items,
            "No files were left without an MXXX module assignment.",
        ),
        "errors": template_list(summary.errors, "No errors occurred."),
    }

    return markdown_to_html(replace_template_variables(load_email_template(), values))


def send_summary_email(summary: Summary, config: Config) -> None:
    try:
        import resend
    except ImportError as error:
        # Keep the error user-friendly so they know exactly which package is missing.
        raise RuntimeError(
            "The 'resend' package is missing. Install it with: pip install resend"
        ) from error

    # The API key can come either from the config file or from an environment variable.
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


def ask_path(label: str, current_value: str) -> str:
    entered = input(f"{label} [{current_value}]: ").strip()
    return entered or current_value


def is_valid_email(value: str) -> bool:
    return EMAIL_PATTERN.fullmatch(value.strip()) is not None


def ask_email(label: str, current_value: str) -> str:
    while True:
        entered = input(f"{label} [{current_value}]: ").strip()
        if not entered:
            return current_value
        if is_valid_email(entered):
            return entered
        print("Please enter a full email address, for example hello@example.com.")


def ask_days(current_value: int | None) -> int | None:
    current_label = "off" if current_value is None else str(current_value)
    entered = input(f"Skip files newer than how many days? [{current_label}, empty=off]: ").strip()
    if not entered:
        return None
    try:
        days = int(entered)
    except ValueError:
        print("Please enter a whole number. Keeping previous value.")
        return current_value
    return max(days, 0)


def has_resend_api_key(config: Config) -> bool:
    config_key = config.resend_api_key
    config_key = config_key.strip()
    env_key = os.environ.get("RESEND_API_KEY", "")
    env_key = env_key.strip()

    if config_key != "":
        return True
    else:
        if env_key != "":
            return True
        else:
            return False


def refresh_python_package_paths() -> None:
    # When pip installs a package, Python does not always notice it immediately, so we refresh its search paths.
    importlib.invalidate_caches()
    try:
        user_site = site.getusersitepackages()
    except (AttributeError, RuntimeError):
        user_site = ""
    if user_site and user_site not in sys.path:
        site.addsitedir(user_site)


def has_resend_package() -> bool:
    refresh_python_package_paths()
    return importlib.util.find_spec("resend") is not None


def install_resend_package() -> bool:
    print("\nThe Resend Python package is not installed yet.")
    print("Installing it now with pip...")
    try:
        subprocess.check_call(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "-r",
                str(APP_DIR / "requirements.txt"),
            ]
        )
    except (OSError, subprocess.CalledProcessError) as error:
        print(f"Automatic installation failed: {error}")
        print("You can install it manually with: pip install -r .\\requirements.txt")
        return False
    refresh_python_package_paths()
    return has_resend_package()


def edit_email_settings(config: Config, force_api_key: bool = False) -> None:
    print("\nEmail Summary Settings")
    print("----------------------")
    print("The Resend API key is stored only in the local ignored config file.")
    print("You can also set RESEND_API_KEY as an environment variable instead.")

    current_key = "set" if has_resend_api_key(config) else "missing"
    print(f"Resend API key: {current_key}")
    if force_api_key or input("Change local Resend API key? [y/N]: ").strip().lower() == "y":
        entered_key = input("Resend API key: ").strip()
        if entered_key:
            config.resend_api_key = entered_key
        elif force_api_key and not has_resend_api_key(config):
            print("A Resend API key is required before cleaning can start.")

    config.email_from = ask_email("Sender email", config.email_from)
    config.email_to = ask_email("Recipient email", config.email_to)
    config.save()


def edit_excluded_paths(config: Config) -> None:
    while True:
        print("\nExcluded paths/files")
        if config.excluded_paths:
            for index, path in enumerate(config.excluded_paths, start=1):
                print(f"{index}. {path}")
        else:
            print("No paths are excluded.")

        print("\n1. Add path/file")
        print("2. Remove path/file")
        print("3. Back")
        choice = input("Choose: ").strip()

        if choice == "1":
            path = input("Path or file to exclude: ").strip().strip('"')
            if path:
                config.excluded_paths.append(path)
                config.save()
        elif choice == "2":
            index_text = input("Number to remove: ").strip()
            if index_text.isdigit():
                index = int(index_text) - 1
                if 0 <= index < len(config.excluded_paths):
                    config.excluded_paths.pop(index)
                    config.save()
        elif choice == "3":
            return


def edit_excluded_patterns(config: Config) -> None:
    current = ", ".join(config.excluded_patterns) or "none"
    print(f"\nCurrent excluded MXXX patterns: {current}")
    entered = input("Enter patterns separated by commas, or leave empty to clear: ").strip()
    config.excluded_patterns = normalize_patterns(
        part.strip() for part in entered.split(",") if part.strip()
    )
    config.save()


def change_paths(config: Config) -> None:
    print("\nChange folders. Press Enter to keep the current value.")
    config.downloads_path = ask_path("Downloads folder", config.downloads_path)
    config.images_path = ask_path("Images/Bilder folder", config.images_path)
    config.videos_path = ask_path("Videos folder", config.videos_path)
    config.desktop_path = ask_path("Desktop folder", config.desktop_path)
    config.save()


def config_menu(config: Config) -> None:
    while True:
        print("\nConfig")
        print("------")
        print(f"Downloads: {config.downloads_path}")
        print(f"Images:    {config.images_path}")
        print(f"Videos:    {config.videos_path}")
        print(f"Desktop:   {config.desktop_path}")
        print(f"Skip newer than days: {config.exclude_newer_than_days or 'off'}")
        print(f"Excluded MXXX patterns: {', '.join(config.excluded_patterns) or 'none'}")
        print(f"Excluded paths/files: {len(config.excluded_paths)}")
        print(f"Resend API key: {'set' if has_resend_api_key(config) else 'missing'}")
        print(f"Summary email to: {config.email_to}")

        print("\n1. Exclude specific paths/files")
        print("2. Exclude files not older than x days")
        print("3. Exclude a specific MXXX pattern")
        print("4. Change paths")
        print("5. Email summary settings")
        print("6. Back")
        choice = input("Choose: ").strip()

        if choice == "1":
            edit_excluded_paths(config)
        elif choice == "2":
            config.exclude_newer_than_days = ask_days(config.exclude_newer_than_days)
            config.save()
        elif choice == "3":
            edit_excluded_patterns(config)
        elif choice == "4":
            change_paths(config)
        elif choice == "5":
            edit_email_settings(config)
        elif choice == "6":
            return


def ensure_email_ready(config: Config) -> bool:
    if not has_resend_package() and not install_resend_package():
        return False

    if has_resend_api_key(config):
        return True

    print("\nStart Cleaning requires a Resend API key first.")
    print("Opening Config so you can add it before the cleaner runs.")
    edit_email_settings(config, force_api_key=True)
    return has_resend_api_key(config)


def main() -> int:
    config = Config.load()

    while True:
        print("\nDownloads Sorter")
        print("----------------")
        print("1. Start Cleaning")
        print("2. Config")
        print("3. Exit")
        choice = input("Choose: ").strip()

        if choice == "1":
            if not ensure_email_ready(config):
                input("\nPress Enter to continue...")
                continue
            summary = clean_downloads(config)
            try:
                send_summary_email(summary, config)
                print("\nCleaning finished. Detailed summary email sent.")
            except RuntimeError as error:
                print(f"\nCleaning finished, but the summary email could not be sent: {error}")
            input("\nPress Enter to continue...")
        elif choice == "2":
            config_menu(config)
        elif choice == "3":
            return 0
        else:
            print("Please choose 1, 2, or 3.")


if __name__ == "__main__":
    sys.exit(main())
