"""
OneDrive utility functions for handling online-only files.
On Windows, requires pywin32 (install with: pip install pywin32)
On non-Windows systems, OneDrive checks are skipped.
"""
import sys
import os

IS_WINDOWS = sys.platform == "win32"

def is_onedrive_file(path: str) -> bool:
    """Simple heuristic: OneDrive in path"""
    return IS_WINDOWS and "OneDrive" in os.path.abspath(path)
