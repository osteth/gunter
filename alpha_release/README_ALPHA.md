## GUNTER (Alpha)

### What to send to testers

Put these files together in one folder:

- `gunter.py`
- `master_list.csv`
- `EGG ICON.ico` (optional, for nicer icon)
- `VERSION`
- `INSTALL_GUNTER.bat` (double-click installer)
- `INSTALL_GUNTER.ps1` (installer script)

### How to run (Windows)

Option A (recommended): run the installer

- Double-click `INSTALL_GUNTER.bat`

Option B: run directly (portable)

1. Install Python 3.10+ (from python.org) and make sure **“Add Python to PATH”** is enabled.
2. Open the folder and run:

```powershell
python gunter.py
```

If they don’t want a console window, use the app menu:
- **File → Create Launch Shortcut…**

### How to use (quick)

- The app loads `master_list.csv` automatically.
- To sync completion from an export:
  - **File → Import new Export.txt…** (recommended), or
  - Click **Sync from Export**
- Importing an export will **sync + auto-create** `stamp_progress.json`.
- Progress is **saved automatically** when you click checkboxes.
- Use **Hide Completed** to focus on remaining stamps.

