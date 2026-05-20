from pathlib import Path
import json
import re
import shutil
from dataclasses import dataclass, field


CONFIG_FILE = Path("sorter_config.json")
MODULE_PATTERN = re.compile(r"M\d{3}", re.IGNORECASE)

IMAGE_EXTENSIONS = [".jpg", ".jpeg", ".png", ".gif", ".bmp"]
VIDEO_EXTENSIONS = [".mp4", ".mov", ".avi", ".mkv"]


@dataclass
class SorterConfig:
    downloads_path: str = str(Path.home() / "Downloads")
    desktop_path: str = str(Path.home() / "Desktop")
    images_path: str = str(Path.home() / "Pictures")
    videos_path: str = str(Path.home() / "Videos")
    excluded_paths: list[str] = field(default_factory=list)


def load_config():
    """Very early config loader. Needs validation later."""
    if not CONFIG_FILE.exists():
        config = SorterConfig()
        CONFIG_FILE.write_text(json.dumps(config.__dict__, indent=2), encoding="utf-8")
        return config

    data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    return SorterConfig(
        downloads_path=data.get("downloads_path", str(Path.home() / "Downloads")),
        desktop_path=data.get("desktop_path", str(Path.home() / "Desktop")),
        images_path=data.get("images_path", str(Path.home() / "Pictures")),
        videos_path=data.get("videos_path", str(Path.home() / "Videos")),
        excluded_paths=data.get("excluded_paths", []),
    )


def find_module_name(filename):
    match = MODULE_PATTERN.search(filename)
    if match:
        return match.group(0).upper()
    return None


def move_file(file_path, destination_folder):
    """Move a file, but duplicate filename handling is not finished yet."""
    destination_folder.mkdir(parents=True, exist_ok=True)
    destination = destination_folder / file_path.name

    if destination.exists():
        print("TODO: handle duplicate file:", destination)
        return False

    shutil.move(str(file_path), str(destination))
    return True


def sort_module_files(downloads_folder, desktop_folder):
    """Move files with module names like M122 to matching Desktop folders."""
    moved = 0

    for file_path in downloads_folder.iterdir():
        if not file_path.is_file():
            continue

        module_name = find_module_name(file_path.name)
        if module_name is None:
            continue

        destination_folder = desktop_folder / module_name
        if move_file(file_path, destination_folder):
            moved += 1

    return moved


def sort_media_files(downloads_folder, image_folder, video_folder):
    """First rough media sorter. More file types need to be added."""
    images_moved = 0
    videos_moved = 0

    for file_path in downloads_folder.iterdir():
        if not file_path.is_file():
            continue

        extension = file_path.suffix.lower()
        if extension in IMAGE_EXTENSIONS:
            if move_file(file_path, image_folder):
                images_moved += 1
        elif extension in VIDEO_EXTENSIONS:
            if move_file(file_path, video_folder):
                videos_moved += 1

    return images_moved, videos_moved


def delete_zip_files(downloads_folder):
    """Unfinished cleanup: should probably check excluded paths first."""
    deleted = 0

    for file_path in downloads_folder.iterdir():
        if file_path.suffix.lower() == ".zip":
            print("Deleting zip file:", file_path.name)
            file_path.unlink()
            deleted += 1

    return deleted


def send_email_report(summary):
    """Placeholder for the later Resend email report feature."""
    print("TODO: send email report")
    print(summary)


def run_sorter():
    config = load_config()

    downloads_folder = Path(config.downloads_path)
    desktop_folder = Path(config.desktop_path)
    image_folder = Path(config.images_path)
    video_folder = Path(config.videos_path)

    summary = {
        "module_files_moved": sort_module_files(downloads_folder, desktop_folder),
        "images_moved": 0,
        "videos_moved": 0,
        "zip_files_deleted": 0,
    }

    images_moved, videos_moved = sort_media_files(
        downloads_folder,
        image_folder,
        video_folder,
    )
    summary["images_moved"] = images_moved
    summary["videos_moved"] = videos_moved
    summary["zip_files_deleted"] = delete_zip_files(downloads_folder)

    print("Download folder sorting finished.")
    print(summary)

    # TODO: only send report when API key and recipient are configured.
    # send_email_report(summary)


if __name__ == "__main__":
    # TODO: add command line options and a dry-run mode.
    run_sorter()
