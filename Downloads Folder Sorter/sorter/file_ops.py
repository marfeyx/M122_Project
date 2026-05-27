from __future__ import annotations

import shutil
from pathlib import Path
from zipfile import BadZipFile, ZipFile

from .models import MoveResult, Summary


def unique_destination(destination: Path) -> Path:
    """

    Args:
        destination (Path): _description_

    Returns:
        Path: _description_
    """
    if not destination.exists():
        return destination

    counter = 1
    while True:
        candidate = destination.with_name(
            f"{destination.stem} ({counter}){destination.suffix}"
        )
        if not candidate.exists():
            return candidate
        counter += 1


def move_file(source: Path, destination_folder: Path) -> MoveResult:
    """

    Args:
        source (Path): _description_
        destination_folder (Path): _description_

    Returns:
        MoveResult: _description_
    """
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
    """

    Args:
        summary (Summary): _description_
        source (Path): _description_
        result (MoveResult): _description_
    """
    if result.duplicate_name:
        summary.duplicate_name_items.append(
            (
                str(source),
                str(result.requested_destination),
                str(result.destination),
            )
        )


def extracted_zip_exists(zip_path: Path, downloads_path: Path) -> bool:
    """

    Args:
        zip_path (Path): _description_
        downloads_path (Path): _description_

    Returns:
        bool: _description_
    """
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
        if (downloads_path / top_level_name).is_dir():
            return True

    return False
