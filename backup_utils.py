import os
import shutil
from pathlib import Path
from typing import List, Dict
from config import EXCLUDE_DIRS, EXCLUDE_EXTENSIONS, MAX_FILE_SIZE_MB
from onedrive_utils import is_onedrive_file

class BackupManager:
    def __init__(self, max_file_size_mb: int = None):
        self.excluded_dirs = set(EXCLUDE_DIRS)
        self.excluded_extensions = set(EXCLUDE_EXTENSIONS)
        self.max_file_size_mb = max_file_size_mb or MAX_FILE_SIZE_MB
        self.skipped_files: List[Dict] = []
        self.onedrive_files: List[Dict] = []

    def _format_size(self, size_mb: float) -> str:
        if size_mb < 1: return f"{size_mb*1024:.0f}KB"
        if size_mb < 1024: return f"{size_mb:.1f}MB"
        return f"{size_mb/1024:.1f}GB"

    def _add_skipped(self, path: str, reason: str):
        size_mb = os.path.getsize(path) / (1024*1024) if os.path.isfile(path) else 0
        self.skipped_files.append({
            "path": path,
            "filename": os.path.basename(path),
            "size_mb": size_mb,
            "reason": reason
        })

    def _should_skip(self, path: str) -> bool:
        parts = Path(path).parts
        if any(d in self.excluded_dirs for d in parts):
            self._add_skipped(path, "Excluded directory")
            return True
        if any(path.lower().endswith(ext.lower()) for ext in self.excluded_extensions):
            self._add_skipped(path, "Excluded extension")
            return True
        if os.path.isfile(path):
            size_mb = os.path.getsize(path) / (1024*1024)
            if size_mb > self.max_file_size_mb:
                self._add_skipped(path, f"File size {self._format_size(size_mb)} > {self.max_file_size_mb}MB")
                return True
        return False

    def _copy_file(self, src: str, dst: str) -> bool:
        try:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
            return True
        except Exception as e:
            self._add_skipped(src, f"Failed to copy: {e}")
            return False

    def _build_dst_index(self, dst_root: str) -> dict:
        """Build relative path -> (size, mtime) for all files in destination."""
        dst_index = {}
        for root, _, files in os.walk(dst_root):
            for f in files:
                full_path = os.path.join(root, f)
                rel_path = os.path.relpath(full_path, dst_root)
                try:
                    stat = os.stat(full_path)
                    dst_index[rel_path] = (stat.st_size, stat.st_mtime)
                except OSError:
                    continue
        return dst_index

    # Backup if file is not already up-to-date, or if file size is larger
    def backup_directory(self, src: str, dst: str):
        src = os.path.abspath(src)
        dst = os.path.abspath(dst)
        self.skipped_files = []
        self.onedrive_files = []

        if not os.path.exists(src):
            print(f"Source does not exist: {src}")
            return

        print(f"\nBacking up {src} -> {dst}")
        print(f"Skipping files larger than {self.max_file_size_mb}MB")
        print(f"Excluding directories: {', '.join(sorted(self.excluded_dirs))}")
        print("-"*50)

        total_files = 0
        copied_files = 0

        # Build index of destination files for fast skip checking
        dst_index = self._build_dst_index(dst)

        for root, dirs, files in os.walk(src, topdown=True):
            dirs[:] = [d for d in dirs if not self._should_skip(os.path.join(root, d))]

            for file in files:
                total_files += 1
                src_path = os.path.join(root, file)

                # Handle strange file names and paths
                try:
                    # First try the normal relative path
                    rel_path = os.path.relpath(src_path, src)
                except ValueError:
                    # If that fails (different drives or special paths), use a different approach
                    try:
                        # Try to get a relative path from the common parent
                        common = os.path.commonpath([os.path.normpath(src_path), os.path.normpath(src)])
                        rel_path = os.path.relpath(os.path.normpath(src_path), common)
                    except (ValueError, TypeError):
                        # If all else fails, use a path relative to the source root
                        rel_path = os.path.basename(src_path)
                
                # Clean up any potential path issues
                rel_path = rel_path.replace('\\', '/')
                dst_path = os.path.normpath(os.path.join(dst, rel_path))

                if self._should_skip(src_path):
                    continue

                # Skip if destination already up-to-date
                src_stat = os.stat(src_path)
                if rel_path in dst_index:
                    dst_size, dst_mtime = dst_index[rel_path]

                    # If file size is same, and source file is older or same age, skip
                    if src_stat.st_size == dst_size and src_stat.st_mtime <= dst_mtime:
                        self._add_skipped(src_path, "Already up-to-date")
                        continue

                # Defer OneDrive files
                if is_onedrive_file(src_path):
                    self.onedrive_files.append({"src": src_path, "dst": dst_path})
                    continue

                if self._copy_file(src_path, dst_path):
                    copied_files += 1

        # Copy OneDrive files last
        for item in self.onedrive_files:
            if self._copy_file(item["src"], item["dst"]):
                copied_files += 1

        # Summary
        skipped_count = len(self.skipped_files)
        print("\n" + "="*80)
        if skipped_count:
            print("\nSkipped files:")
            print(f"{'File':<50} | {'Size':<10} | Reason")
            print("-"*80)
            for item in sorted(self.skipped_files, key=lambda x: x["size_mb"], reverse=True):
                print(f"{item['filename'][:48]:<50} | {self._format_size(item['size_mb']):<10} | {item['reason']}")
    
        print("="*80)
        print(f"Backup completed!")
        print(f"Total files scanned: {total_files}")
        print(f"Files copied: {copied_files}")
        print(f"Files skipped: {skipped_count}")
        print("="*80)
