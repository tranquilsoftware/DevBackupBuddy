"""
Disk utilities for detecting available drives and managing file operations.
"""
import os
import shutil
import string
from pathlib import Path
from typing import List, Tuple

def get_available_drives() -> List[str]:
    """Get a list of available drives (excluding system drive)."""
    system_drive = os.environ.get('SystemDrive', 'C:')
    available_drives = [f"{d}:\\" for d in string.ascii_uppercase 
                       if os.path.exists(f"{d}:") and f"{d}:\\" != system_drive]
    return available_drives

def is_valid_destination(destination: str) -> bool:
    """Check if the destination path is valid and writable."""
    try:
        test_file = os.path.join(destination, '.test')
        with open(test_file, 'w') as f:
            f.write('test')
        os.remove(test_file)
        return True
    except (IOError, OSError):
        return False

def create_backup_directory(base_path: str, dir_name: str) -> str:
    """Create a new directory for the backup."""
    backup_path = os.path.join(base_path, dir_name)
    os.makedirs(backup_path, exist_ok=True)
    return backup_path
