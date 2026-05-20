from __future__ import annotations

import sys

from sorter import (
    Config,
    MoveResult,
    Summary,
    clean_downloads,
    default_config,
    main,
    send_summary_email,
    summary_email_html,
)
from sorter.cli import (
    ask_days,
    ask_email,
    ask_path,
    change_paths,
    config_menu,
    edit_email_settings,
    edit_excluded_paths,
    edit_excluded_patterns,
    ensure_email_ready,
    has_resend_api_key,
    has_resend_package,
    install_resend_package,
    refresh_python_package_paths,
)
from sorter.email_summary import (
    load_email_template,
    markdown_code,
    markdown_inline_to_html,
    markdown_to_html,
    replace_template_variables,
    template_list,
)
from sorter.file_ops import (
    extracted_zip_exists,
    move_file,
    record_duplicate_name,
    unique_destination,
)
from sorter.paths import is_inside, known_folder_path, resolve_path
from sorter.patterns import find_modules, is_valid_email, normalize_patterns
from sorter.settings import APP_DIR, CONFIG_PATH, EMAIL_TEMPLATE_PATH
from sorter.sorting import (
    IMAGE_EXTENSIONS,
    PARTIAL_DOWNLOAD_EXTENSIONS,
    VIDEO_EXTENSIONS,
    choose_module_folder,
    delete_extracted_zips,
    desktop_module_folders,
    exclusion_reason,
    is_excluded,
)

__all__ = [
    "APP_DIR",
    "CONFIG_PATH",
    "EMAIL_TEMPLATE_PATH",
    "Config",
    "IMAGE_EXTENSIONS",
    "MoveResult",
    "PARTIAL_DOWNLOAD_EXTENSIONS",
    "Summary",
    "VIDEO_EXTENSIONS",
    "ask_days",
    "ask_email",
    "ask_path",
    "change_paths",
    "choose_module_folder",
    "clean_downloads",
    "config_menu",
    "default_config",
    "delete_extracted_zips",
    "desktop_module_folders",
    "edit_email_settings",
    "edit_excluded_paths",
    "edit_excluded_patterns",
    "ensure_email_ready",
    "exclusion_reason",
    "extracted_zip_exists",
    "find_modules",
    "has_resend_api_key",
    "has_resend_package",
    "install_resend_package",
    "is_excluded",
    "is_inside",
    "is_valid_email",
    "known_folder_path",
    "load_email_template",
    "main",
    "markdown_code",
    "markdown_inline_to_html",
    "markdown_to_html",
    "move_file",
    "normalize_patterns",
    "record_duplicate_name",
    "refresh_python_package_paths",
    "replace_template_variables",
    "resolve_path",
    "send_summary_email",
    "summary_email_html",
    "template_list",
    "unique_destination",
]


if __name__ == "__main__":
    sys.exit(main())
