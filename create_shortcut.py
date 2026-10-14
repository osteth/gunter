#!/usr/bin/env python3
"""
Script to create a desktop shortcut for GUNTER application.
"""

import os
import sys
from pathlib import Path

def create_shortcut():
    """Create a desktop shortcut for GUNTER."""
    # Get paths
    script_dir = Path(__file__).parent.absolute()
    desktop = Path(r'C:\Users\gregg\OneDrive\Desktop')
    gunter_script = script_dir / 'gunter.py'
    icon_file = script_dir / 'EGG ICON.ico'  # Prefer ICO format
    if not icon_file.exists():
        icon_file = script_dir / 'EGG ICON.jpeg'  # Fallback to JPEG
    python_exe = sys.executable
    
    # Try using win32com (Windows COM interface)
    try:
        import win32com.client
        from win32com.client import Dispatch
        
        # Create shortcut
        shell = Dispatch('WScript.Shell')
        shortcut_path = desktop / 'GUNTER.lnk'
        shortcut = shell.CreateShortCut(str(shortcut_path))
        
        # Set target to python executable with gunter.py
        shortcut.Targetpath = python_exe
        shortcut.Arguments = f'"{gunter_script}"'
        shortcut.WorkingDirectory = str(script_dir)
        shortcut.Description = 'GUNTER - Quest Stamp Tracker'
        
        # Set icon if available
        if icon_file.exists():
            shortcut.IconLocation = str(icon_file)
        
        shortcut.save()
        print(f"Desktop shortcut created: {shortcut_path}")
        return True
        
    except ImportError:
        # Fallback: Create a batch file
        print("win32com not available, creating batch file instead...")
        batch_file = desktop / 'GUNTER.bat'
        
        with open(batch_file, 'w') as f:
            f.write(f'@echo off\n')
            f.write(f'cd /d "{script_dir}"\n')
            f.write(f'"{python_exe}" "{gunter_script}"\n')
            f.write(f'pause\n')
        
        print(f"Batch file created: {batch_file}")
        print("Note: For a proper shortcut with icon, install pywin32: pip install pywin32")
        return True
    except Exception as e:
        print(f"Error creating shortcut: {e}")
        return False

if __name__ == '__main__':
    create_shortcut()
