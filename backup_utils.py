"""
Core backup functionality.
"""
import os
import shutil
from pathlib import Path
from typing import List, Set
from config import EXCLUDE_DIRS, EXCLUDE_EXTENSIONS

class BackupManager:
    def __init__(self):
        self.excluded_dirs = set(EXCLUDE_DIRS)
        self.excluded_extensions = set(EXCLUDE_EXTENSIONS)
    
    def should_skip(self, path: str) -> bool:
        """Check if a path should be skipped based on exclusion rules."""
        path_parts = Path(path).parts
        
        # Skip system files and directories
        if any(part.startswith('.') and part not in ('.', '..') for part in path_parts):
            return True
            
        # Skip excluded directories
        if any(excluded in path_parts for excluded in self.excluded_dirs):
            return True
            
        # Skip excluded file extensions
        if any(path.lower().endswith(ext.lower()) for ext in self.excluded_extensions):
            return True
            
        return False
    
    def copy_file(self, src: str, dst: str) -> None:
        """Copy a single file with error handling."""
        try:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
            print(f"Copied: {src}")
        except (IOError, OSError) as e:
            print(f"Error copying {src}: {e}")
    
    def backup_directory(self, src: str, dst: str) -> None:
        """Backup a directory recursively."""
        src = os.path.abspath(src)
        dst = os.path.abspath(dst)
        
        if not os.path.exists(src):
            print(f"Source directory does not exist: {src}")
            return
            
        print(f"\nStarting backup from: {src}")
        print(f"Destination: {dst}")
        print("Excluding:", ', '.join(sorted(self.excluded_dirs)))
        print("-" * 50)
        
        for root, dirs, files in os.walk(src, topdown=True):
            # Skip excluded directories
            dirs[:] = [d for d in dirs if not self.should_skip(os.path.join(root, d))]
            
            for file in files:
                src_path = os.path.join(root, file)
                rel_path = os.path.relpath(src_path, src)
                dst_path = os.path.join(dst, rel_path)
                
                if not self.should_skip(src_path):
                    self.copy_file(src_path, dst_path)
        
        print("\nBackup completed!")
