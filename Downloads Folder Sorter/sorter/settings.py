from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = APP_DIR / "sorter_config.json"
EMAIL_TEMPLATE_PATH = APP_DIR / "email_template.md"
