## GUNTER (Alpha)

### What to send to testers

Put these files together in one folder:

- `gunter.py`
- `master_list.csv`
- `VERSION`
- `INSTALL_GUNTER.bat` (double-click installer)
- `UPGRADE_GUNTER.bat` (double-click upgrade)
- `UNINSTALL_GUNTER.bat` (double-click uninstall)

Folders included:
- `images\` (icons)
- `scripts\` (support scripts used by the .bat files)

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

- Use the **Account/Profile** selector to track multiple accounts separately.
- The app loads `master_list.csv` automatically.
- To sync completion from an export:
  - **File → Import new Export.txt…** (recommended), or
  - Drag a Utility Belt export into the drop zone
- Importing an export will **sync + auto-create** `stamp_progress.json`.
- Progress is **saved automatically** when you click checkboxes.
- (Optional) Enable **Auto-sync from folder** and point it at the folder where UtilityBelt writes exports. GUNTER will auto-sync the newest `questbonuses_export_YYYYMMDD_HHMMSS.txt`.
- Use **Hide Completed** to focus on remaining stamps.

