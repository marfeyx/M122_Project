from __future__ import annotations

import importlib
import importlib.util
import os
import site
import subprocess
import sys

from .config import Config
from .email_summary import send_summary_email
from .patterns import is_valid_email, normalize_patterns
from .settings import APP_DIR
from .sorting import clean_downloads


def ask_path(label: str, current_value: str) -> str:
    entered = input(f"{label} [{current_value}]: ").strip()
    return entered or current_value


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
    config_key = config.resend_api_key.strip()
    env_key = os.environ.get("RESEND_API_KEY", "").strip()
    return bool(config_key or env_key)


def refresh_python_package_paths() -> None:
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
