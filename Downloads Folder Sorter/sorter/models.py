from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


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
