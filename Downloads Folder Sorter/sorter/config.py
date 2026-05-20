from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from .paths import known_folder_path
from .patterns import is_valid_email, normalize_patterns
from .settings import CONFIG_PATH


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
        defaults = default_config()
        if not CONFIG_PATH.exists():
            defaults.save()
            return defaults

        try:
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            print("Config file could not be read. Default settings will be used.")
            return defaults

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


def default_config() -> Config:
    home = Path.home()
    return Config(
        downloads_path=str(known_folder_path("downloads", home / "Downloads")),
        desktop_path=str(known_folder_path("desktop", home / "Desktop")),
        images_path=str(known_folder_path("pictures", home / "Pictures")),
        videos_path=str(known_folder_path("videos", home / "Videos")),
    )
