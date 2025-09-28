"""
Disk utilities for detecting available drives and managing file operations.
"""
import os
import string
from typing import List

def get_available_drives() -> List[str]:
    system_drive = os.environ.get("SystemDrive", "C:")
    drives = [f"{d}:\\" for d in string.ascii_uppercase if os.path.exists(f"{d}:") and f"{d}:\\" != system_drive]
    return drives

def is_valid_destination(destination: str) -> bool:
    try:
        test_file = os.path.join(destination, ".test")
        with open(test_file, "w") as f:
            f.write("test")
        os.remove(test_file)
        return True
    except (OSError, IOError):
        return False