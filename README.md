# Downloads Sorter

![Unit test coverage:](badges/coverage.svg)

Windows console app that cleans a Downloads folder by moving school/project files into matching desktop folders.

## Features

- Sorts files and folders by `MXXX`, `DE`, `GR`, `FR`, and `PH` naming patterns.
- Creates missing desktop folders and reuses existing matching folders.
- Moves unsorted images and videos into Pictures/Bilder and Videos.
- Deletes `.zip` files when the extracted folder already exists.
- Supports exclusions by path, age, and pattern.
- Sends a Resend email summary after each run.

## Setup

```powershell
cd ".\Downloads Folder Sorter"
pip install -r .\requirements.txt
```

Set a Resend API key in the app config or with:

```powershell
$env:RESEND_API_KEY = "your-api-key"
```

## Run

```powershell
python .\download_sorter.py
```

The first run creates a local `sorter_config.json`, which is ignored by Git. Use the `Config` menu to change folder paths, exclusions, and email settings.

Edit `email_template.md` to customize the summary email.
