"""
Core backup functionality.
"""
import os
import shutil
from pathlib import Path
from typing import List, Set, Optional
import os
from config import EXCLUDE_DIRS, EXCLUDE_EXTENSIONS, MAX_FILE_SIZE_MB

class BackupManager:
    def __init__(self):
        self.excluded_dirs = set(EXCLUDE_DIRS)
        self.excluded_extensions = set(EXCLUDE_EXTENSIONS)
        self.skipped_files = []  # To store skipped files and their sizes
    
    def should_skip(self, path: str) -> bool:
        """Check if a path should be skipped based on exclusion rules and file size."""
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
            
        # Check file size if it's a file
        if os.path.isfile(path):
            file_size_mb = os.path.getsize(path) / (1024 * 1024)  # Convert bytes to MB
            if file_size_mb > MAX_FILE_SIZE_MB:
                self.skipped_files.append((os.path.basename(path), file_size_mb))
                print(f"Skipping large file ({file_size_mb:.2f}MB): {path}")
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
    
    def _format_size(self, size_mb: float) -> str:
        """Format file size in a human-readable format."""
        if size_mb < 1:
            return f"{size_mb*1024:.0f}KB"
        elif size_mb < 1024:
            return f"{size_mb:.1f}MB"
        else:
            return f"{size_mb/1024:.1f}GB"
    
    def backup_directory(self, src: str, dst: str) -> None:
        """Backup a directory recursively, skipping files larger than MAX_FILE_SIZE_MB."""
        src = os.path.abspath(src)
        dst = os.path.abspath(dst)
        self.skipped_files = []  # Reset skipped files list for each backup
        
        if not os.path.exists(src):
            print(f"Source directory does not exist: {src}")
            return
            
        print(f"\nStarting backup from: {src}")
        print(f"Destination: {dst}")
        print(f"Skipping files larger than {MAX_FILE_SIZE_MB}MB")
        print("Excluding:", ', '.join(sorted(self.excluded_dirs)))
        print("-" * 50)
        
        total_files = 0
        skipped_files = 0
        
        for root, dirs, files in os.walk(src, topdown=True):
            # Skip excluded directories
            dirs[:] = [d for d in dirs if not self.should_skip(os.path.join(root, d))]
            
            for file in files:
                total_files += 1
                src_path = os.path.join(root, file)
                rel_path = os.path.relpath(src_path, src)
                dst_path = os.path.join(dst, rel_path)
                
                if not self.should_skip(src_path):
                    self.copy_file(src_path, dst_path)
                else:
                    skipped_files += 1
        
        # Print summary
        print("\n" + "=" * 50)
        print(f"Backup completed!")
        print(f"Total files processed: {total_files}")
        print(f"Files skipped: {skipped_files}")
        print(f"Files copied: {total_files - skipped_files}")
        
        # Print skipped files if any
        if self.skipped_files:
            print(f"\nSkipped files (larger than {MAX_FILE_SIZE_MB}MB):")
            print("-" * 50)
            # Sort by size in descending order
            for filename, size_mb in sorted(self.skipped_files, key=lambda x: x[1], reverse=True):
                print(f"- {filename} ({self._format_size(size_mb)})")
        
        print("=" * 50)
