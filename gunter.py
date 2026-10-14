#!/usr/bin/env python3
"""
GUNTER - Quest Stamp Tracker GUI Application
Interactive interface for tracking quest stamp completion progress.
"""

import csv
import json
import os
import shutil
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import List, Dict, Set, Tuple
import webbrowser
import ctypes
import re

# Optional: drag & drop support (Windows-friendly) via tkinterdnd2
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD  # type: ignore
    DND_AVAILABLE = True
except ImportError:
    DND_AVAILABLE = False

# simpledialog for profile prompts
from tkinter import simpledialog

# Try to import PIL for icon support
try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


# Core logic functions (from find_missing_stamps.py)
def read_completed_stamps(file_path: str) -> Set[str]:
    """Read completed stamps from a text file."""
    completed_stamps = set()
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Completed stamps file not found: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
        # Find the separator line (starts with dashes) and start reading after it
        start_idx = 0
        for i, line in enumerate(lines):
            if line.strip().startswith('---'):
                start_idx = i + 1
                break
        
        # If no separator found, skip first 6 lines (header format)
        if start_idx == 0:
            start_idx = 6
        
        # Process from start_idx until we hit the summary line or end of file
        for line in lines[start_idx:]:
            line = line.strip()
            # Stop if we hit the summary line
            if line.startswith('[UB]'):
                break
            # Add non-empty lines as stamps
            if line:
                completed_stamps.add(line)
    
    return completed_stamps


def read_all_stamps(file_path: str) -> List[Dict[str, str]]:
    """Read all stamps from CSV file."""
    all_stamps_data = []
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Wiki stamps CSV file not found: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            stamp_name = row.get('stamp_name', '').strip()
            if stamp_name:
                all_stamps_data.append(row)
    
    return all_stamps_data


def _normalize_stamp_name(name: str) -> str:
    """Normalize stamp names for more robust matching."""
    # Note: master list may contain known typos (e.g., "Recieved" vs "Received").
    return name.strip().lower().replace('recieved', 'received')


def _build_completed_index(completed_stamps: Set[str]) -> Tuple[Set[str], Dict[Tuple[int, str], List[str]]]:
    """Build a fast index for completed stamp matching."""
    normalized_set: Set[str] = set()
    by_len_prefix: Dict[Tuple[int, str], List[str]] = {}
    for stamp in completed_stamps:
        n = _normalize_stamp_name(stamp)
        if not n:
            continue
        normalized_set.add(n)
        prefix = n[:2] if len(n) >= 2 else n
        by_len_prefix.setdefault((len(n), prefix), []).append(n)
    return normalized_set, by_len_prefix


def is_stamp_completed(stamp_name: str, completed_norm_set: Set[str], completed_index: Dict[Tuple[int, str], List[str]]) -> bool:
    """Return True if stamp_name is found in completed stamps (fast, tolerant)."""
    n = _normalize_stamp_name(stamp_name)
    if not n:
        return False
    if n in completed_norm_set:
        return True

    prefix2 = n[:2] if len(n) >= 2 else n
    candidates: List[str] = []
    for L in (len(n) - 1, len(n), len(n) + 1):
        if L <= 0:
            continue
        candidates.extend(completed_index.get((L, prefix2), []))

    # If the prefix2 bucket is empty, broaden to prefix1 (still far smaller than full scan)
    if not candidates and n:
        prefix1 = n[:1]
        for L in (len(n) - 1, len(n), len(n) + 1):
            if L <= 0:
                continue
            candidates.extend(completed_index.get((L, prefix1), []))

    if not candidates:
        return False

    # Lightweight typo/transposition tolerance within the candidate bucket
    for c in candidates:
        if c == n:
            return True

        if len(c) == len(n) and len(n) > 5:
            diff = sum(1 for a, b in zip(c, n) if a != b)
            if diff <= 2:
                return True

        if abs(len(c) - len(n)) <= 1 and len(n) > 5 and c[0] == n[0]:
            c_set = set(c)
            n_set = set(n)
            similarity = len(c_set & n_set) / max(len(c_set), len(n_set))
            if similarity >= 0.95:
                return True

    return False


class GUNTERApp:
    """Main application class for GUNTER."""
    
    def __init__(self, root):
        self.root = root
        self.root.title(f"GUNTER {self.get_version()}")
        # Wide by default so the Info column is visible without scrolling.
        self.root.geometry("1500x800")
        
        # File paths
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.export_file_path = None
        self.master_list_path = os.path.join(self.script_dir, 'master_list.csv')

        # User data (profiles, settings, per-account progress)
        self.user_data_dir = self.get_user_data_dir()
        self.profiles_dir = os.path.join(self.user_data_dir, "profiles")
        os.makedirs(self.profiles_dir, exist_ok=True)
        self.settings_path = os.path.join(self.user_data_dir, "settings.json")

        self.settings = {}
        self.active_profile_id = None
        self.progress_file = ""  # per-profile progress file path (set after settings load)
        
        # Set application icon
        self.set_icon()
        
        # Data storage
        self.stamps_data = []    # full master list rows
        self.progress_data = {}  # stamp_name -> bool
        self.filtered_data = []  # Currently displayed data
        self.sort_column = None
        self.sort_reverse = False

        # View options
        self.hide_completed_var = tk.BooleanVar(value=False)

        # Auto-sync options (per profile)
        self.auto_sync_enabled_var = tk.BooleanVar(value=False)
        self.auto_sync_dir_var = tk.StringVar(value="")
        self._watch_last_mtime = None
        self._watch_last_path = None
        self._watch_job = None
        
        # Setup dark theme
        self.setup_dark_theme()
        
        # Create GUI
        self.create_widgets()

        # Load settings/profiles and initial progress
        self.load_settings()
        self.ensure_default_profile()
        self.apply_profile(self.active_profile_id)
        
        # Auto-load master list + Export.txt sync (if present) on launch
        self.auto_load_on_launch()

    @staticmethod
    def _parse_dnd_files(data: str) -> List[str]:
        """
        Parse a tkinterdnd2 DND_FILES string into file paths.
        On Windows, paths with spaces are typically wrapped in {...}.
        """
        if not data:
            return []

        paths: List[str] = []
        i = 0
        n = len(data)
        while i < n:
            # Skip whitespace
            while i < n and data[i].isspace():
                i += 1
            if i >= n:
                break

            if data[i] == "{":
                i += 1
                start = i
                while i < n and data[i] != "}":
                    i += 1
                paths.append(data[start:i])
                # Skip closing brace
                if i < n and data[i] == "}":
                    i += 1
            else:
                start = i
                while i < n and not data[i].isspace():
                    i += 1
                paths.append(data[start:i])

        # Normalize/strip
        cleaned = []
        for p in paths:
            p = p.strip().strip('"')
            if p:
                cleaned.append(p)
        return cleaned

    def import_export_file_from_path(self, src_path: str):
        """Copy an export file into app dir as Export.txt and sync progress."""
        if not src_path or not os.path.exists(src_path):
            messagebox.showerror("Error", f"Export file not found:\n{src_path}")
            return

        dst_path = os.path.join(self.script_dir, 'Export.txt')
        try:
            shutil.copy2(src_path, dst_path)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to import Export.txt:\n{e}")
            return

        self.export_file_path = dst_path

        # Sync + auto-save progress (creates stamp_progress.json)
        self.sync_from_export()
        # Convenience: set auto-sync folder from the original file (per profile), but don't auto-enable.
        try:
            folder = os.path.dirname(src_path)
            self.auto_sync_dir_var.set(folder)
            self.persist_profile_autosync_settings()
        except Exception:
            pass

    def persist_profile_autosync_settings(self):
        """Save auto-sync settings into the current profile."""
        p = self.get_profile(self.active_profile_id) if self.active_profile_id else None
        if not p:
            return
        p["auto_sync_enabled"] = bool(self.auto_sync_enabled_var.get())
        p["auto_sync_dir"] = str(self.auto_sync_dir_var.get() or "")
        self.save_settings()

    def on_profile_selected(self):
        """Handle user switching profile from combobox."""
        name = self.profile_var.get()
        for p in self.settings.get("profiles", []):
            if p.get("name") == name:
                self.apply_profile(p.get("id"))
                return

    def refresh_profile_combo(self):
        names = [p.get("name", p.get("id")) for p in self.settings.get("profiles", [])]
        self.profile_combo["values"] = names
        # keep selection
        current = self.get_profile(self.active_profile_id) if self.active_profile_id else None
        if current:
            self.profile_var.set(current.get("name", current.get("id")))

    def add_profile(self):
        name = simpledialog.askstring("New Profile", "Profile name (e.g. Account1):", parent=self.root)
        if not name:
            return
        name = name.strip()
        if not name:
            return

        # unique id
        base = "".join(c.lower() if c.isalnum() else "-" for c in name).strip("-") or "profile"
        pid = base
        existing_ids = {p.get("id") for p in self.settings.get("profiles", [])}
        i = 2
        while pid in existing_ids:
            pid = f"{base}-{i}"
            i += 1

        progress_path = os.path.join(self.profiles_dir, f"{pid}.json")
        profile = {
            "id": pid,
            "name": name,
            "progress_file": progress_path,
            "auto_sync_enabled": False,
            "auto_sync_dir": "",
        }
        self.settings["profiles"].append(profile)
        self.save_settings()
        self.refresh_profile_combo()
        self.apply_profile(pid)

    def rename_profile(self):
        p = self.get_profile(self.active_profile_id) if self.active_profile_id else None
        if not p:
            return
        new_name = simpledialog.askstring("Rename Profile", "New profile name:", initialvalue=p.get("name", ""), parent=self.root)
        if not new_name:
            return
        p["name"] = new_name.strip()
        self.save_settings()
        self.refresh_profile_combo()

    def delete_profile(self):
        profiles = self.settings.get("profiles", [])
        if len(profiles) <= 1:
            messagebox.showinfo("Info", "You must have at least one profile.")
            return
        p = self.get_profile(self.active_profile_id) if self.active_profile_id else None
        if not p:
            return
        ok = messagebox.askyesno("Delete Profile", f"Delete profile '{p.get('name')}'?\n\nThis will NOT delete your master list.\nIt will delete that profile's saved progress file.", parent=self.root)
        if not ok:
            return

        # delete progress file
        try:
            prog = p.get("progress_file")
            if prog and os.path.exists(prog):
                os.remove(prog)
        except Exception:
            pass

        self.settings["profiles"] = [x for x in profiles if x.get("id") != p.get("id")]
        # switch to first remaining
        self.active_profile_id = self.settings["profiles"][0]["id"]
        self.settings["active_profile_id"] = self.active_profile_id
        self.save_settings()
        self.refresh_profile_combo()
        self.apply_profile(self.active_profile_id)

    def on_auto_sync_toggle(self):
        self.persist_profile_autosync_settings()
        self.start_or_stop_watch()

    def _on_autosync_fields_changed(self, *_args):
        self.persist_profile_autosync_settings()

    def select_auto_sync_file(self):
        path = filedialog.askdirectory(
            title="Select folder where UtilityBelt exports questbonuses files",
            initialdir=os.path.expanduser("~"),
            mustexist=True,
        )
        if not path:
            return
        self.auto_sync_dir_var.set(path)
        self.persist_profile_autosync_settings()
        if self.auto_sync_enabled_var.get():
            self.start_or_stop_watch()

    def start_or_stop_watch(self):
        if self._watch_job:
            try:
                self.root.after_cancel(self._watch_job)
            except Exception:
                pass
            self._watch_job = None
        self._watch_last_mtime = None
        self._watch_last_path = None

        if bool(self.auto_sync_enabled_var.get()) and str(self.auto_sync_dir_var.get() or "").strip():
            self._watch_job = self.root.after(1500, self.poll_auto_sync_file)

    def poll_auto_sync_file(self):
        """Poll the configured export folder; if a newer export appears, sync."""
        self._watch_job = None
        if not bool(self.auto_sync_enabled_var.get()):
            return
        folder = str(self.auto_sync_dir_var.get() or "").strip()
        if not folder or not os.path.isdir(folder):
            return

        try:
            latest_path, latest_mtime = self._find_latest_export_file(folder)
            if latest_path and latest_mtime is not None:
                if self._watch_last_mtime is None:
                    self._watch_last_mtime = latest_mtime
                    self._watch_last_path = latest_path
                elif (latest_mtime > self._watch_last_mtime) or (latest_path != self._watch_last_path and latest_mtime == self._watch_last_mtime):
                    self._watch_last_mtime = latest_mtime
                    self._watch_last_path = latest_path
                    self.sync_from_export_path(latest_path)
        except Exception:
            # ignore and keep trying
            pass

        self._watch_job = self.root.after(1500, self.poll_auto_sync_file)

    @staticmethod
    def _find_latest_export_file(folder: str) -> tuple[str | None, float | None]:
        """
        Return (path, mtime) for newest matching export in folder.
        Matches:
          questbonuses_export_YYYYMMDD_HHMMSS.txt
        """
        pattern = re.compile(r"^questbonuses_export_\d{8}_\d{6}\.txt$", re.IGNORECASE)

        best_path = None
        best_mtime = None
        try:
            for name in os.listdir(folder):
                if not pattern.match(name):
                    continue
                p = os.path.join(folder, name)
                try:
                    mt = os.path.getmtime(p)
                except Exception:
                    continue
                if best_mtime is None or mt > best_mtime or (mt == best_mtime and (best_path is None or name > os.path.basename(best_path))):
                    best_mtime = mt
                    best_path = p
        except Exception:
            return None, None
        return best_path, best_mtime

    def sync_from_export_path(self, export_path: str):
        """Sync progress by reading directly from a Utility Belt export file path."""
        if not export_path or not os.path.exists(export_path):
            return

        # Update active export file path for sync logic
        self.export_file_path = export_path

        # Do the same work as sync_from_export, but read from export_path
        try:
            self.status_label.config(text="Auto-syncing...", foreground='#ffff00')
            self.root.update()

            completed_stamps = read_completed_stamps(export_path)
            completed_norm_set, completed_index = _build_completed_index(completed_stamps)

            if not self.stamps_data:
                self.stamps_data = read_all_stamps(self.master_list_path)

            matched = 0
            for stamp in self.stamps_data:
                stamp_name = stamp.get('stamp_name', '').strip()
                if not stamp_name:
                    continue
                if is_stamp_completed(stamp_name, completed_norm_set, completed_index):
                    if not self.progress_data.get(stamp_name, False):
                        matched += 1
                    self.progress_data[stamp_name] = True
                else:
                    self.progress_data.setdefault(stamp_name, False)

            self.save_progress()
            self.populate_table()
            self.status_label.config(text=f"Auto-synced {matched} new completed stamps", foreground='#00ff00')
        except Exception:
            # ignore errors during polling
            pass

    def get_version(self) -> str:
        """Read VERSION file from app directory (fallback to 'dev')."""
        try:
            version_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "VERSION")
            if os.path.exists(version_path):
                with open(version_path, "r", encoding="utf-8") as f:
                    v = f.read().strip()
                    return v if v else "dev"
        except Exception:
            pass
        return "dev"

    def get_user_data_dir(self) -> str:
        """Return a writable per-user data directory."""
        if sys.platform.startswith("win"):
            base = os.getenv("LOCALAPPDATA") or self.script_dir
            path = os.path.join(base, "GUNTER")
        else:
            path = self.script_dir
        os.makedirs(path, exist_ok=True)
        return path

    def load_settings(self):
        """Load settings.json (profiles, last active profile, per-profile config)."""
        self.settings = {}
        if os.path.exists(self.settings_path):
            try:
                with open(self.settings_path, "r", encoding="utf-8") as f:
                    self.settings = json.load(f) or {}
            except Exception:
                self.settings = {}

        self.settings.setdefault("profiles", [])
        self.active_profile_id = self.settings.get("active_profile_id")

    def save_settings(self):
        """Persist settings.json."""
        try:
            os.makedirs(os.path.dirname(self.settings_path), exist_ok=True)
            with open(self.settings_path, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=2)
        except Exception:
            # non-fatal
            pass

    def ensure_default_profile(self):
        """Create a default profile if none exist; attempt to migrate old stamp_progress.json."""
        profiles = self.settings.get("profiles", [])
        if profiles:
            if not self.active_profile_id:
                self.active_profile_id = profiles[0]["id"]
                self.settings["active_profile_id"] = self.active_profile_id
                self.save_settings()
            return

        default_id = "default"
        default_progress = os.path.join(self.profiles_dir, f"{default_id}.json")
        os.makedirs(self.profiles_dir, exist_ok=True)

        # migrate old progress if present in app dir
        old_progress = os.path.join(self.script_dir, "stamp_progress.json")
        if os.path.exists(old_progress) and not os.path.exists(default_progress):
            try:
                with open(old_progress, "r", encoding="utf-8") as f:
                    data = json.load(f)
                with open(default_progress, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
            except Exception:
                pass

        profile = {
            "id": default_id,
            "name": "Default",
            "progress_file": default_progress,
            "auto_sync_enabled": False,
            "auto_sync_path": "",
        }
        self.settings["profiles"] = [profile]
        self.active_profile_id = default_id
        self.settings["active_profile_id"] = default_id
        self.save_settings()

    def get_profile(self, profile_id: str):
        for p in self.settings.get("profiles", []):
            if p.get("id") == profile_id:
                return p
        return None

    def apply_profile(self, profile_id: str):
        """Switch active profile/account and reload progress + autosync settings."""
        p = self.get_profile(profile_id) if profile_id else None
        if not p:
            return

        self.active_profile_id = p["id"]
        self.settings["active_profile_id"] = self.active_profile_id
        self.save_settings()

        self.progress_file = p.get("progress_file") or os.path.join(self.profiles_dir, f"{p['id']}.json")
        p["progress_file"] = self.progress_file

        # Load progress for this profile
        self.load_progress()
        # Reload master list display
        self.load_master_list_and_display()

        # Apply per-profile autosync state
        self.auto_sync_enabled_var.set(bool(p.get("auto_sync_enabled", False)))
        # Back-compat: if old setting exists, derive folder
        if "auto_sync_dir" in p:
            self.auto_sync_dir_var.set(str(p.get("auto_sync_dir", "")))
        elif "auto_sync_path" in p and p.get("auto_sync_path"):
            ap = str(p.get("auto_sync_path"))
            self.auto_sync_dir_var.set(os.path.dirname(ap))
        else:
            self.auto_sync_dir_var.set("")
        self.start_or_stop_watch()

        # Update UI selector if present
        if hasattr(self, "profile_var"):
            self.profile_var.set(p.get("name", p["id"]))
    
    def setup_dark_theme(self):
        """Configure dark mode theme."""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Dark color scheme
        bg_color = '#2b2b2b'
        fg_color = '#ffffff'
        select_bg = '#404040'
        select_fg = '#ffffff'
        entry_bg = '#3c3c3c'
        button_bg = '#404040'
        button_active = '#505050'
        
        # Configure root background
        self.root.configure(bg=bg_color)
        
        # Configure ttk styles
        style.configure('TFrame', background=bg_color)
        style.configure('TLabel', background=bg_color, foreground=fg_color)
        style.configure('TButton', 
                       background=button_bg, 
                       foreground=fg_color,
                       borderwidth=1,
                       focuscolor='none')
        style.map('TButton',
                 background=[('active', button_active), ('pressed', '#606060')])
        style.configure('TEntry',
                       fieldbackground=entry_bg,
                       foreground=fg_color,
                       borderwidth=1,
                       insertcolor=fg_color)
        style.configure('Treeview',
                       background=entry_bg,
                       foreground=fg_color,
                       fieldbackground=entry_bg,
                       rowheight=25)
        style.configure('Treeview.Heading',
                       background=button_bg,
                       foreground=fg_color,
                       relief='flat')
        style.map('Treeview',
                 background=[('selected', select_bg)],
                 foreground=[('selected', select_fg)])
        style.map('Treeview.Heading',
                 background=[('active', button_active)])
    
    def set_icon(self):
        """Set the application icon."""
        # Help Windows associate this process with our shortcuts (taskbar icon).
        try:
            if sys.platform.startswith("win"):
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("GUNTER")  # type: ignore[attr-defined]
        except Exception:
            pass

        # Prefer Windows .ico (no Pillow required)
        ico_path = os.path.join(self.script_dir, 'images', 'EGG ICON.ico')
        if os.path.exists(ico_path):
            try:
                # Windows Tk supports iconbitmap(.ico) (affects window + taskbar in most cases)
                self.root.iconbitmap(ico_path)
                try:
                    # Also set as default icon for any future toplevels
                    self.root.iconbitmap(default=ico_path)  # type: ignore[call-arg]
                except Exception:
                    pass

                # If Pillow exists, also set via iconphoto for extra reliability
                if PIL_AVAILABLE:
                    try:
                        img = Image.open(ico_path)
                        photo = ImageTk.PhotoImage(img)
                        self.root.iconphoto(True, photo)
                        self.icon_photo = photo
                    except Exception:
                        pass
                return
            except Exception:
                # If iconbitmap fails, fall back to iconphoto methods below
                pass

        # Fallback: JPEG (requires Pillow for reliable support)
        jpg_path = os.path.join(self.script_dir, 'images', 'EGG ICON.jpeg')
        if not os.path.exists(jpg_path):
            return

        try:
            if PIL_AVAILABLE:
                img = Image.open(jpg_path)
                img = img.resize((256, 256), Image.Resampling.LANCZOS) if hasattr(Image, 'Resampling') else img.resize((256, 256), Image.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                self.root.iconphoto(True, photo)
                self.icon_photo = photo
            else:
                # tk.PhotoImage typically doesn't support JPEG; skip silently
                return
        except Exception:
            pass
    
    def create_widgets(self):
        """Create and layout all GUI widgets."""
        # Menu bar
        menubar = tk.Menu(self.root)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Import new Export.txt...", command=self.import_new_export_file)
        file_menu.add_command(label="Import new master_list.csv...", command=self.import_new_master_list)
        file_menu.add_command(label="Sync from Export", command=self.sync_from_export)
        file_menu.add_separator()
        file_menu.add_command(label="Create Launch Shortcut...", command=self.create_launch_shortcut)
        file_menu.add_separator()
        file_menu.add_command(label="Save Progress As...", command=self.save_progress_manual)
        file_menu.add_command(label="Load Progress...", command=self.load_progress_manual)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        menubar.add_cascade(label="File", menu=file_menu)
        self.root.config(menu=menubar)

        # Top frame - File selection
        top_frame = ttk.Frame(self.root, padding="4")
        top_frame.pack(fill=tk.X, padx=10, pady=(6, 2))

        # Right side: drag & drop (so it fills the top-right space)
        top_right_frame = ttk.Frame(top_frame)
        top_right_frame.pack(side=tk.RIGHT, padx=(10, 0), pady=(0, 0), anchor="n")

        self.drop_target = tk.Label(
            top_right_frame,
            text="Drag Utility Belt\nQB export here\nto Sync",
            bg="#3c3c3c",
            fg="#ffffff",
            relief="ridge",
            bd=2,
            width=22,
            height=6,
            padx=10,
            pady=10,
            cursor="hand2",
            justify="center",
        )
        self.drop_target.pack()
        self.drop_target.bind("<Button-1>", lambda _e: self.import_new_export_file())

        if DND_AVAILABLE:
            try:
                self.drop_target.drop_target_register(DND_FILES)  # type: ignore[attr-defined]
                self.drop_target.dnd_bind("<<Drop>>", self.on_export_drop)  # type: ignore[attr-defined]
            except Exception:
                self.drop_target.config(text="Drag & drop\nunavailable", cursor="")
        else:
            self.drop_target.config(text="Drag & drop\nunavailable", cursor="")

        # Left side: stacked controls
        top_left_frame = ttk.Frame(top_frame)
        top_left_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Profile/account selection
        profile_frame = ttk.Frame(top_left_frame)
        profile_frame.pack(fill=tk.X, pady=(0, 4))

        ttk.Label(profile_frame, text="Account/Profile:").pack(side=tk.LEFT, padx=5)
        self.profile_var = tk.StringVar(value="")
        self.profile_combo = ttk.Combobox(profile_frame, textvariable=self.profile_var, state="readonly", width=25)
        self.profile_combo.pack(side=tk.LEFT, padx=5)
        self.profile_combo.bind("<<ComboboxSelected>>", lambda _e: self.on_profile_selected())

        ttk.Button(profile_frame, text="Add", command=self.add_profile).pack(side=tk.LEFT, padx=2)
        ttk.Button(profile_frame, text="Rename", command=self.rename_profile).pack(side=tk.LEFT, padx=2)
        ttk.Button(profile_frame, text="Delete", command=self.delete_profile).pack(side=tk.LEFT, padx=2)

        # Persist autosync field edits (per profile)
        self.auto_sync_dir_var.trace_add("write", self._on_autosync_fields_changed)

        # Auto-sync controls (per profile)
        autosync_frame = ttk.Frame(top_left_frame)
        autosync_frame.pack(fill=tk.X, pady=(0, 2))

        autosync_controls = ttk.Frame(autosync_frame)
        autosync_controls.pack(side=tk.LEFT)

        ttk.Checkbutton(
            autosync_controls,
            text="Auto-sync from folder:",
            variable=self.auto_sync_enabled_var,
            command=self.on_auto_sync_toggle,
        ).pack(side=tk.LEFT, padx=5)

        self.auto_sync_entry = ttk.Entry(autosync_controls, textvariable=self.auto_sync_dir_var, width=60)
        # Keep this compact; full path is still stored/used.
        self.auto_sync_entry.pack(side=tk.LEFT, padx=5)
        ttk.Button(autosync_controls, text="Browse...", command=self.select_auto_sync_file).pack(side=tk.LEFT, padx=(0, 5))

        # Status line (sync feedback) — inline to save vertical space
        self.status_label = ttk.Label(autosync_frame, text="", foreground="#888888", anchor="w")
        self.status_label.pack(side=tk.LEFT, padx=(10, 0), fill=tk.X, expand=True)

        # Search frame (kept inside header to reduce vertical gaps)
        search_frame = ttk.Frame(top_left_frame)
        search_frame.pack(fill=tk.X, pady=(0, 0))
        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT, padx=5)
        self.search_var = tk.StringVar()
        self.search_var.trace('w', lambda *args: self.filter_table())
        # Fixed width so there's room for a larger drop pad on the right.
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=65)
        search_entry.pack(side=tk.LEFT, padx=5)

        # Hide completed toggle (next to search)
        hide_completed_cb = ttk.Checkbutton(
            search_frame,
            text="Hide Completed",
            variable=self.hide_completed_var,
            command=self.filter_table,
        )
        hide_completed_cb.pack(side=tk.LEFT, padx=(10, 5))
        
        # Table frame with scrollbars
        table_frame = ttk.Frame(self.root)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 8))
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        h_scrollbar = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Treeview table
        columns = ('completed', 'stamp_name', 'quest_name', 'quest_url', 'info')
        self.tree = ttk.Treeview(table_frame, columns=columns, show='headings', 
                                yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set,
                                selectmode='extended')
        
        # Store original column header texts
        self.column_headers = {
            'completed': '✓',
            'stamp_name': 'Stamp Name',
            'quest_name': 'Quest Name',
            'quest_url': 'Quest URL',
            'info': 'Info',
        }
        
        # Configure columns
        self.tree.heading('completed', text='✓', command=lambda: self.sort_by_column('completed'))
        self.tree.heading('stamp_name', text='Stamp Name', command=lambda: self.sort_by_column('stamp_name'))
        self.tree.heading('quest_name', text='Quest Name', command=lambda: self.sort_by_column('quest_name'))
        self.tree.heading('quest_url', text='Quest URL', command=lambda: self.sort_by_column('quest_url'))
        self.tree.heading('info', text='Info', command=lambda: self.sort_by_column('info'))
        
        self.tree.column('completed', width=50, anchor=tk.CENTER)
        self.tree.column('stamp_name', width=220, anchor=tk.W)
        self.tree.column('quest_name', width=260, anchor=tk.W)
        self.tree.column('quest_url', width=320, anchor=tk.W)
        self.tree.column('info', width=600, anchor=tk.W)
        
        # Bind checkbox clicks and URL double-clicks
        self.tree.bind('<Button-1>', self.on_tree_click)
        self.tree.bind('<Double-Button-1>', self.on_tree_double_click)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        v_scrollbar.config(command=self.tree.yview)
        h_scrollbar.config(command=self.tree.xview)
        
        # Info label
        info_frame = ttk.Frame(self.root, padding="6")
        info_frame.pack(fill=tk.X, padx=10, pady=(2, 4))
        self.info_label = ttk.Label(info_frame, text="No data loaded", foreground='#888888')
        self.info_label.pack(side=tk.LEFT)
    
    def auto_load_on_launch(self):
        """Automatically load master list, then sync from Export.txt if present."""
        # Always show the master list using saved progress first (fast path).
        self.root.after(50, self.load_master_list_and_display)

        export_file = os.path.join(self.script_dir, 'Export.txt')
        if os.path.exists(export_file):
            self.export_file_path = export_file
        else:
            # Check for alternative names (case-insensitive)
            for file in os.listdir(self.script_dir):
                if file.lower() == 'export.txt':
                    self.export_file_path = os.path.join(self.script_dir, file)
                    break

        if self.export_file_path and os.path.exists(self.export_file_path):
            # Sync after UI is ready
            self.root.after(150, self.sync_from_export)
    
    def select_export_file(self):
        """Open file dialog to select export file."""
        file_path = filedialog.askopenfilename(
            title="Select Export File",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialdir=self.script_dir
        )
        if file_path:
            self.export_file_path = file_path
    
    def select_master_list(self):
        """Open file dialog to select master list CSV."""
        file_path = filedialog.askopenfilename(
            title="Select Master List CSV",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialdir=self.script_dir,
            initialfile='master_list.csv'
        )
        if file_path:
            self.master_list_path = file_path
            # Reload list to reflect newly selected master list
            self.load_master_list_and_display()

    def import_new_export_file(self):
        """Import a new export file into the app directory as Export.txt (overwrite)."""
        src_path = filedialog.askopenfilename(
            title="Import new Export.txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialdir=self.script_dir,
        )
        if not src_path:
            return
        self.import_export_file_from_path(src_path)

    def on_export_drop(self, event):
        """Handle drag-and-drop of Utility Belt export files."""
        try:
            paths = self._parse_dnd_files(getattr(event, "data", ""))
            if not paths:
                return
            # Use first dropped file
            self.import_export_file_from_path(paths[0])
        except Exception as e:
            messagebox.showerror("Error", f"Failed to import dropped file:\n{e}")

    def import_new_master_list(self):
        """Import a new master list into the app directory as master_list.csv (overwrite)."""
        src_path = filedialog.askopenfilename(
            title="Import new master_list.csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialdir=self.script_dir,
        )
        if not src_path:
            return

        dst_path = os.path.join(self.script_dir, 'master_list.csv')
        try:
            shutil.copy2(src_path, dst_path)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to import master_list.csv:\n{e}")
            return

        # Always use master_list.csv as the single source of truth
        self.master_list_path = dst_path

        # Reload master list and resync against export if available
        self.stamps_data = []
        self.load_master_list_and_display()
        if self.export_file_path and os.path.exists(self.export_file_path):
            self.sync_from_export()

    def create_launch_shortcut(self):
        """Create a launcher shortcut without opening a console window."""
        dest_dir = filedialog.askdirectory(
            title="Choose where to create the shortcut",
            initialdir=os.path.expanduser("~"),
            mustexist=True,
        )
        if not dest_dir:
            return

        script_dir = self.script_dir
        gunter_script = os.path.join(script_dir, "gunter.py")
        python_exe = sys.executable
        python_dir = os.path.dirname(python_exe)
        pythonw_exe = os.path.join(python_dir, "pythonw.exe")
        python_gui_exe = pythonw_exe if os.path.exists(pythonw_exe) else python_exe

        # Prefer ICO for shortcuts
        icon_file = os.path.join(script_dir, "images", "EGG ICON.ico")
        if not os.path.exists(icon_file):
            icon_file = os.path.join(script_dir, "images", "EGG ICON.jpeg")

        lnk_path = os.path.join(dest_dir, "GUNTER.lnk")
        vbs_path = os.path.join(dest_dir, "GUNTER.vbs")

        # Overwrite confirmation if any exists
        if os.path.exists(lnk_path) or os.path.exists(vbs_path):
            ok = messagebox.askyesno(
                "Overwrite?",
                "A GUNTER shortcut already exists in that folder.\n\nOverwrite it?",
            )
            if not ok:
                return

        # Try creating a real Windows shortcut via pywin32; fallback to .vbs (no console)
        try:
            from win32com.client import Dispatch  # type: ignore

            shell = Dispatch("WScript.Shell")
            shortcut = shell.CreateShortCut(str(lnk_path))
            shortcut.Targetpath = python_gui_exe
            shortcut.Arguments = f"\"{gunter_script}\""
            shortcut.WorkingDirectory = str(script_dir)
            shortcut.Description = "GUNTER - Quest Stamp Tracker"
            if os.path.exists(icon_file):
                shortcut.IconLocation = str(icon_file)
            shortcut.save()

            messagebox.showinfo("Shortcut Created", f"Created shortcut:\n{lnk_path}")
            return
        except Exception:
            # Fallback: VBS launcher (runs hidden)
            try:
                # 0 = hidden window, False = don't wait
                vbs = (
                    'Set WshShell = CreateObject("WScript.Shell")\n'
                    f'WshShell.CurrentDirectory = "{script_dir}"\n'
                    f'WshShell.Run Chr(34) & "{python_gui_exe}" & Chr(34) & " " & Chr(34) & "{gunter_script}" & Chr(34), 0, False\n'
                )
                with open(vbs_path, "w", encoding="utf-8") as f:
                    f.write(vbs)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to create shortcut:\n{e}")
                return

            messagebox.showinfo(
                "Launcher Created",
                f"Created launcher:\n{vbs_path}\n\n"
                "Tip: For a proper .lnk with icon, install pywin32:\n"
                "python -m pip install --user pywin32",
            )
            return
    
    def load_progress(self):
        """Load saved progress from JSON file."""
        if self.progress_file and os.path.exists(self.progress_file):
            try:
                with open(self.progress_file, 'r', encoding='utf-8') as f:
                    self.progress_data = json.load(f)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load progress: {e}")
                self.progress_data = {}
        else:
            self.progress_data = {}

    # NOTE: We intentionally only read from master_list.csv.
    # Any enrichment/cleanup should be done to master_list.csv itself (offline scripts),
    # rather than producing alternative master list filenames.
    
    def save_progress(self):
        """Save progress to JSON file (auto-save on every checkbox change)."""
        try:
            # Ensure directory exists
            progress_dir = os.path.dirname(self.progress_file) if self.progress_file else ""
            if progress_dir and not os.path.exists(progress_dir):
                os.makedirs(progress_dir)
            
            # Save to file
            if self.progress_file:
                with open(self.progress_file, 'w', encoding='utf-8') as f:
                    json.dump(self.progress_data, f, indent=2)
            
            # Brief visual feedback (optional - can be removed if too distracting)
            # The status label will show briefly that it saved
        except Exception as e:
            # Show error but don't block the UI
            messagebox.showerror("Error", f"Failed to save progress: {e}")
    
    def save_progress_manual(self):
        """Save progress to a user-selected JSON file."""
        if not self.progress_data:
            messagebox.showinfo("Info", "No data to save.")
            return
        
        file_path = filedialog.asksaveasfilename(
            title="Save Progress and Quest List",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialdir=self.script_dir,
            initialfile="gunter_save.json"
        )
        
        if file_path:
            try:
                save_data = {
                    'progress': self.progress_data,
                    'export_file': self.export_file_path,
                    'master_list': self.master_list_path
                }
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(save_data, f, indent=2)
                
                progress_count = len(self.progress_data)
                messagebox.showinfo("Success", 
                    f"Data saved to:\n{file_path}\n\n"
                    f"Progress entries: {progress_count}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save data: {e}")
    
    def load_progress_manual(self):
        """Load progress from a user-selected JSON file."""
        file_path = filedialog.askopenfilename(
            title="Load Progress and Quest List",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialdir=self.script_dir
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    loaded_data = json.load(f)
                
                # Handle both old format (just progress) and new format (structured)
                if isinstance(loaded_data, dict) and 'progress' in loaded_data:
                    # New format with structured data
                    self.progress_data = loaded_data.get('progress', {}).copy()
                    # Restore file paths if saved
                    if 'export_file' in loaded_data and loaded_data['export_file']:
                        self.export_file_path = loaded_data['export_file']
                    if 'master_list' in loaded_data and loaded_data['master_list']:
                        self.master_list_path = loaded_data['master_list']

                    self.load_master_list_and_display()
                    messagebox.showinfo("Success",
                        f"Progress loaded from:\n{file_path}\n\n"
                        f"{len(self.progress_data)} progress entries loaded.")
                else:
                    # Old format - just progress data
                    self.progress_data = loaded_data.copy()
                    
                    self.load_master_list_and_display()
                    
                    messagebox.showinfo("Success", 
                        f"Progress loaded from:\n{file_path}\n\n"
                        f"{len(self.progress_data)} progress entries loaded.\n\n"
                        f"Note: This file uses the old format.")
                
                # Update default progress file path
                self.progress_file = file_path
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load data: {e}")

    def load_master_list_and_display(self):
        """Load master list CSV and populate the table using saved progress."""
        if not os.path.exists(self.master_list_path):
            self.info_label.config(text="Master list not found", foreground='#ff6666')
            return

        try:
            self.status_label.config(text="Loading master list...", foreground='#ffff00')
            self.root.update()

            self.stamps_data = read_all_stamps(self.master_list_path)

            # Ensure progress has entries for every stamp in the master list
            for stamp in self.stamps_data:
                stamp_name = stamp.get('stamp_name', '').strip()
                if stamp_name and stamp_name not in self.progress_data:
                    self.progress_data[stamp_name] = False

            self.populate_table()
            self.status_label.config(text=f"Loaded {len(self.stamps_data)} stamps", foreground='#00ff00')
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load master list: {str(e)}")
            self.status_label.config(text="Error occurred", foreground='#ff0000')


    def sync_from_export(self):
        """Mark master list stamps as completed based on Export.txt, then save progress."""
        if not self.export_file_path:
            messagebox.showwarning("Warning", "Please select an export file first.")
            return

        if not os.path.exists(self.master_list_path):
            messagebox.showerror("Error", f"Master list file not found: {self.master_list_path}")
            return

        try:
            self.status_label.config(text="Reading Export.txt...", foreground='#ffff00')
            self.root.update()

            completed_stamps = read_completed_stamps(self.export_file_path)
            completed_norm_set, completed_index = _build_completed_index(completed_stamps)

            # Ensure master list is loaded
            if not self.stamps_data:
                self.stamps_data = read_all_stamps(self.master_list_path)

            # Mark completed stamps (do not auto-uncheck anything)
            matched = 0
            for stamp in self.stamps_data:
                stamp_name = stamp.get('stamp_name', '').strip()
                if not stamp_name:
                    continue
                if is_stamp_completed(stamp_name, completed_norm_set, completed_index):
                    if not self.progress_data.get(stamp_name, False):
                        matched += 1
                    self.progress_data[stamp_name] = True
                else:
                    self.progress_data.setdefault(stamp_name, False)

            self.save_progress()
            self.populate_table()

            self.status_label.config(text=f"Synced {matched} new completed stamps from export", foreground='#00ff00')
        except Exception as e:
            messagebox.showerror("Error", f"Failed to sync from export: {str(e)}")
            self.status_label.config(text="Error occurred", foreground='#ff0000')
    
    def populate_table(self):
        """Populate the table with master list data."""
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Add items
        self.filtered_data = self.stamps_data.copy()
        self.apply_filter()
        self.update_table_display()
    
    def apply_filter(self):
        """Apply search filter to filtered_data."""
        search_term = self.search_var.get().lower()
        hide_completed = bool(self.hide_completed_var.get())

        filtered = []
        for stamp in self.stamps_data:
            stamp_name = stamp.get('stamp_name', '')
            if hide_completed and self.progress_data.get(stamp_name, False):
                continue

            if not search_term:
                filtered.append(stamp)
                continue

            if (
                search_term in stamp_name.lower()
                or search_term in stamp.get('quest_name', '').lower()
                or search_term in stamp.get('quest_url', '').lower()
                or search_term in str(stamp.get('info', '')).lower()
            ):
                filtered.append(stamp)

        self.filtered_data = filtered
    
    def update_table_display(self):
        """Update the table display with current filtered_data."""
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        def sort_value(stamp: Dict[str, str], column: str):
            stamp_name = stamp.get('stamp_name', '')
            if column == 'completed':
                return self.progress_data.get(stamp_name, False)
            return str(stamp.get(column, '')).lower()

        # Sort if needed
        if self.sort_column:
            self.filtered_data.sort(key=lambda x: sort_value(x, self.sort_column), reverse=self.sort_reverse)
        
        # Add items
        for stamp in self.filtered_data:
            stamp_name = stamp.get('stamp_name', '')
            completed = self.progress_data.get(stamp_name, False)
            checkbox = '☑' if completed else '☐'
            
            values = (
                checkbox,
                stamp_name,
                stamp.get('quest_name', ''),
                stamp.get('quest_url', ''),
                stamp.get('info', ''),
            )
            self.tree.insert('', tk.END, values=values, tags=(stamp_name,))
        
        # Update info label
        total = len(self.stamps_data)
        filtered = len(self.filtered_data)
        completed_count = sum(1 for stamp in self.stamps_data 
                              if self.progress_data.get(stamp.get('stamp_name', ''), False))
        if filtered == total:
            self.info_label.config(text=f"Total: {total} stamps | Completed: {completed_count} | Remaining: {total - completed_count}")
        else:
            self.info_label.config(text=f"Showing {filtered} of {total} stamps | Completed: {completed_count} | Remaining: {total - completed_count}")
    
    def filter_table(self):
        """Filter table based on search term."""
        self.apply_filter()
        self.update_table_display()
    
    def update_column_headers(self):
        """Update column headers to show sort indicators."""
        for col, base_text in self.column_headers.items():
            if col == self.sort_column:
                # Add sort indicator
                indicator = ' ↓' if self.sort_reverse else ' ↑'
                self.tree.heading(col, text=base_text + indicator)
            else:
                # Remove indicator
                self.tree.heading(col, text=base_text)
    
    def sort_by_column(self, column):
        """Sort table by column with ascending/descending toggle."""
        if self.sort_column == column:
            # Toggle sort direction
            self.sort_reverse = not self.sort_reverse
        else:
            # New column, start with ascending
            self.sort_column = column
            self.sort_reverse = False
        
        # Update column headers to show sort indicators
        self.update_column_headers()
        
        # Update table display
        self.update_table_display()
    
    def on_tree_click(self, event):
        """Handle clicks on tree items, especially checkbox column."""
        region = self.tree.identify_region(event.x, event.y)
        if region == 'cell':
            column = self.tree.identify_column(event.x)
            item = self.tree.identify_row(event.y)
            
            if column == '#1' and item:  # Checkbox column
                values = list(self.tree.item(item, 'values'))
                # Get stamp_name from tags or from values (second column)
                tags = self.tree.item(item, 'tags')
                if tags:
                    stamp_name = tags[0]
                elif len(values) > 1:
                    stamp_name = values[1]  # stamp_name is in second column
                else:
                    return
                
                if stamp_name:
                    # Toggle completion
                    current = self.progress_data.get(stamp_name, False)
                    self.progress_data[stamp_name] = not current
                    
                    # Update checkbox display
                    checkbox = '☑' if not current else '☐'
                    values[0] = checkbox
                    self.tree.item(item, values=values)
                    
                    # Save progress immediately on every checkbox click
                    self.save_progress()
                    
                    # Update info label
                    total = len(self.stamps_data)
                    filtered = len(self.filtered_data)
                    completed_count = sum(1 for stamp in self.stamps_data 
                                          if self.progress_data.get(stamp.get('stamp_name', ''), False))
                    if filtered == total:
                        self.info_label.config(text=f"Total: {total} stamps | Completed: {completed_count} | Remaining: {total - completed_count}")
                    else:
                        self.info_label.config(text=f"Showing {filtered} of {total} stamps | Completed: {completed_count} | Remaining: {total - completed_count}")
            elif column == '#2' and item:  # Stamp Name column - copy to clipboard
                values = list(self.tree.item(item, 'values'))
                if len(values) > 1:
                    stamp_name = values[1]  # stamp_name is the 2nd column (index 1)
                    if stamp_name:
                        try:
                            self.root.clipboard_clear()
                            self.root.clipboard_append(stamp_name)
                            # Brief visual feedback
                            self.status_label.config(text=f"Copied: {stamp_name[:50]}...", foreground='#00ff00')
                            self.root.after(2000, lambda: self.status_label.config(text="", foreground='#888888'))
                        except Exception as e:
                            messagebox.showerror("Error", f"Failed to copy to clipboard: {e}")
            elif column == '#3' and item:  # Quest Name column - copy to clipboard
                values = list(self.tree.item(item, 'values'))
                if len(values) > 2:
                    quest_name = values[2]  # quest_name is the 3rd column (index 2)
                    if quest_name:
                        try:
                            self.root.clipboard_clear()
                            self.root.clipboard_append(quest_name)
                            # Brief visual feedback
                            self.status_label.config(text=f"Copied: {quest_name[:50]}...", foreground='#00ff00')
                            self.root.after(2000, lambda: self.status_label.config(text="", foreground='#888888'))
                        except Exception as e:
                            messagebox.showerror("Error", f"Failed to copy to clipboard: {e}")
            elif column == '#4' and item:  # Quest URL column - open on single click
                values = list(self.tree.item(item, 'values'))
                if len(values) > 3:
                    url = values[3]  # quest_url is the 4th column (index 3)
                    if url and url.startswith('http'):
                        try:
                            webbrowser.open(url)
                        except Exception as e:
                            messagebox.showerror("Error", f"Failed to open URL: {e}")
    
    def on_tree_double_click(self, event):
        """Handle double-clicks on tree items, especially URL column."""
        region = self.tree.identify_region(event.x, event.y)
        if region == 'cell':
            column = self.tree.identify_column(event.x)
            item = self.tree.identify_row(event.y)
            
            # Check if clicking on quest_url column (column #4)
            if column == '#4' and item:
                values = list(self.tree.item(item, 'values'))
                if len(values) > 3:
                    url = values[3]  # quest_url is the 4th column (index 3)
                    if url and url.startswith('http'):
                        try:
                            webbrowser.open(url)
                        except Exception as e:
                            messagebox.showerror("Error", f"Failed to open URL: {e}")


def main():
    """Main entry point."""
    root = TkinterDnD.Tk() if DND_AVAILABLE else tk.Tk()  # type: ignore[name-defined]
    app = GUNTERApp(root)
    root.mainloop()


if __name__ == '__main__':
    main()
