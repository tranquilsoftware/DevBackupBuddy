"""
Core backup functionality.
"""
import os
import shutil
import sys
from pathlib import Path
from typing import List, Set, Optional
from config import EXCLUDE_DIRS, EXCLUDE_EXTENSIONS, MAX_FILE_SIZE_MB
from onedrive_utils import OneDriveUtils

class BackupManager:
    def __init__(self, max_file_size_mb: int = MAX_FILE_SIZE_MB):
        self.excluded_dirs = set(EXCLUDE_DIRS)
        self.excluded_extensions = set(EXCLUDE_EXTENSIONS)
        self.skipped_files = []  # To store skipped files and their sizes
        self.max_file_size_mb = max_file_size_mb
    
    def should_skip(self, path: str) -> bool:
        """Check if a path should be skipped based on exclusion rules and file size."""
        path_parts = Path(path).parts
        
        # Skip system files and directories
        # THIS EXCLUDES .gitignore, .env which we need!
        # if any(part.startswith('.') and part not in ('.', '..') for part in path_parts):
            # self._add_skipped(path, "System file/directory")
            # return True
            
        # Skip excluded directories
        for excluded in self.excluded_dirs:
            if excluded in path_parts:
                self._add_skipped(path, f"Excluded directory: {excluded}")
                return True
            
        # Skip excluded file extensions
        for ext in self.excluded_extensions:
            if path.lower().endswith(ext.lower()):
                self._add_skipped(path, f"Excluded extension: {ext}")
                return True
            
        # Check file size if it's a file
        if os.path.isfile(path):
            file_size_mb = os.path.getsize(path) / (1024 * 1024)  # Convert bytes to MB
            if file_size_mb > self.max_file_size_mb:
                self._add_skipped(path, f"File size: {self._format_size(file_size_mb)} > {self.max_file_size_mb}MB")
                return True
                
        return False
    
    def _add_skipped(self, path: str, reason: str) -> None:
        """Add a skipped file to the list with its reason for skipping."""
        filename = os.path.basename(path)
        size_mb = os.path.getsize(path) / (1024 * 1024) if os.path.isfile(path) else 0
        self.skipped_files.append({
            'filename': filename,
            'path': path,
            'size_mb': size_mb,
            'reason': reason
        })
    
    def copy_file(self, src: str, dst: str) -> bool:
        """
        Copy a single file with error handling.
        Returns True if file was copied, False if skipped (already exists with same size/mtime)
        """
        try:
            # Only check OneDrive status on Windows
            if sys.platform == 'win32':
                # Ensure the source file is downloaded if it's a OneDrive file
                if OneDriveUtils.is_onedrive_file(src) and not OneDriveUtils.ensure_file_downloaded(src):
                    print(f"Skipped (could not download from OneDrive): {src}")
                    return False
            
            # Get source file stats
            try:
                src_stat = os.stat(src)
            except OSError as e:
                print(f"Error accessing source file {src}: {e}")
                return False
            
            # Check if destination exists and is the same
            if os.path.exists(dst):
                try:
                    dst_stat = os.stat(dst)
                    if src_stat.st_size == dst_stat.st_size and src_stat.st_mtime <= dst_stat.st_mtime:
                        print(f"Skipped (unchanged): {src}")
                        return False
                except OSError:
                    # If we can't stat the destination, continue with copy
                    pass
            
            # Ensure destination directory exists
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            
            # Perform the copy
            shutil.copy2(src, dst)
            
            # Verify the copy was successful
            if os.path.exists(dst):
                dst_size = os.path.getsize(dst)
                if dst_size == src_stat.st_size:
                    print(f"Copied: {src} ({src_stat.st_size} bytes)")
                    return True
                else:
                    print(f"Warning: Incomplete copy - expected {src_stat.st_size} bytes, got {dst_size} bytes: {src}")
                    return False
            else:
                print(f"Error: Failed to copy file: {src}")
                return False
                
        except (IOError, OSError) as e:
            print(f"Error copying {src}: {e}")
            return False
    
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
        print(f"Skipping files larger than {self.max_file_size_mb}MB")
        print("Excluding:", ', '.join(sorted(self.excluded_dirs)))
        print("-" * 50)
        
        total_files = 0
        skipped_files = 0
        copied_files = 0
        
        for root, dirs, files in os.walk(src, topdown=True):
            # Skip excluded directories
            dirs[:] = [d for d in dirs if not self.should_skip(os.path.join(root, d))]
            
            for file in files:
                total_files += 1
                src_path = os.path.join(root, file)
                rel_path = os.path.relpath(src_path, src)
                dst_path = os.path.join(dst, rel_path)
                
                if not self.should_skip(src_path):
                    if self.copy_file(src_path, dst_path):
                        copied_files += 1
                else:
                    skipped_files += 1
        
        # Print summary
        print("\n" + "=" * 100)
        print(f"Backup completed!")
        print(f"Total files processed: {total_files}")
        print(f"Files skipped (excluded): {skipped_files}")
        print(f"Files skipped (unchanged): {total_files - skipped_files - copied_files}")
        print(f"Files copied: {copied_files}")
        
        # Print skipped files if any
        if self.skipped_files:
            print("\nSkipped files:")
            print("-" * 100)
            print(f"{'File':<50} | {'Size':<15} | Reason")
            print("-" * 100)
            # Sort by size in descending order
            for item in sorted(self.skipped_files, key=lambda x: x['size_mb'], reverse=True):
                print(f"{item['filename'][:48]:<50} | {self._format_size(item['size_mb']):<15} | {item['reason']}")
        
        print("=" * 100)
