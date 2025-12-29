"""
File indexing module for DevBackupBuddy.
Provides MD5-based file fingerprinting, indexing, and cache persistence.
"""
import os
import json
import hashlib
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Set
from datetime import datetime
from pathlib import Path
from config import EXCLUDE_DIRS, EXCLUDE_EXTENSIONS, MAX_FILE_SIZE_MB

INDEX_CACHE_FILENAME = ".backup_index.json"
INDEX_VERSION = 1
HASH_CHUNK_SIZE = 8192  # 8KB chunks for MD5 computation


@dataclass
class FileInfo:
    """Information about a single file."""
    relative_path: str   # Path relative to root (normalized with forward slashes)
    md5: str             # MD5 hash of file contents
    mtime: float         # Last modified timestamp
    size: int            # File size in bytes


class FileIndex:
    """
    Index of files with lookups by path and by MD5.
    Enables efficient detection of moved files via content hash matching.
    """
    def __init__(self):
        self.by_path: Dict[str, FileInfo] = {}       # relative_path -> FileInfo
        self.by_md5: Dict[str, List[FileInfo]] = {}  # md5 -> list of FileInfo

    def add(self, file_info: FileInfo):
        """Add a file to the index."""
        self.by_path[file_info.relative_path] = file_info
        if file_info.md5 not in self.by_md5:
            self.by_md5[file_info.md5] = []
        self.by_md5[file_info.md5].append(file_info)

    def get_by_path(self, relative_path: str) -> Optional[FileInfo]:
        """Get file info by relative path."""
        return self.by_path.get(relative_path)

    def get_by_md5(self, md5: str) -> List[FileInfo]:
        """Get all files with a given MD5 hash."""
        return self.by_md5.get(md5, [])

    def all_files(self) -> List[FileInfo]:
        """Get all files in the index."""
        return list(self.by_path.values())

    def __len__(self) -> int:
        return len(self.by_path)


def compute_md5(filepath: str) -> str:
    """Compute MD5 hash of a file using chunked reading."""
    hash_md5 = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(HASH_CHUNK_SIZE), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def normalize_path(path: str) -> str:
    """Normalize path to use forward slashes for consistency."""
    return path.replace("\\", "/")


def should_exclude(
    path: str,
    excluded_dirs: Set[str],
    excluded_extensions: Set[str],
    max_file_size_mb: int
) -> Optional[str]:
    """
    Check if a file/directory should be excluded.
    Returns the reason string if excluded, None if not excluded.
    """
    parts = Path(path).parts

    # Check excluded directories
    for part in parts:
        if part in excluded_dirs:
            return f"Excluded directory: {part}"

    # Check excluded extensions
    for ext in excluded_extensions:
        if path.lower().endswith(ext.lower()):
            return f"Excluded extension: {ext}"

    # Check file size (only for files)
    if os.path.isfile(path):
        try:
            size_mb = os.path.getsize(path) / (1024 * 1024)
            if size_mb > max_file_size_mb:
                return f"File size {size_mb:.1f}MB > {max_file_size_mb}MB"
        except OSError:
            pass

    return None


def build_index(
    root: str,
    excluded_dirs: Set[str] = None,
    excluded_extensions: Set[str] = None,
    max_file_size_mb: int = None,
    cache: Optional[Dict] = None,
    progress_callback=None
) -> tuple[FileIndex, List[Dict]]:
    """
    Build a FileIndex for all files under root.

    Args:
        root: Root directory to index
        excluded_dirs: Set of directory names to exclude
        excluded_extensions: Set of file extensions to exclude
        max_file_size_mb: Maximum file size in MB
        cache: Optional cached index data from previous run
        progress_callback: Optional callback(current, total, filepath) for progress

    Returns:
        Tuple of (FileIndex, list of skipped files with reasons)
    """
    excluded_dirs = excluded_dirs or set(EXCLUDE_DIRS)
    excluded_extensions = excluded_extensions or set(EXCLUDE_EXTENSIONS)
    max_file_size_mb = max_file_size_mb or MAX_FILE_SIZE_MB

    root = os.path.abspath(root)
    index = FileIndex()
    skipped = []

    # Count total files first for progress
    total_files = 0
    for _, _, files in os.walk(root):
        total_files += len(files)

    current_file = 0

    for dirpath, dirnames, filenames in os.walk(root, topdown=True):
        # Filter out excluded directories in-place
        dirnames[:] = [
            d for d in dirnames
            if d not in excluded_dirs
        ]

        for filename in filenames:
            current_file += 1
            filepath = os.path.join(dirpath, filename)

            try:
                rel_path = normalize_path(os.path.relpath(filepath, root))
            except ValueError:
                # Handle edge cases (different drives, etc.)
                rel_path = normalize_path(filename)

            if progress_callback:
                progress_callback(current_file, total_files, rel_path)

            # Check exclusions
            exclude_reason = should_exclude(
                filepath, excluded_dirs, excluded_extensions, max_file_size_mb
            )
            if exclude_reason:
                try:
                    size = os.path.getsize(filepath) if os.path.isfile(filepath) else 0
                except OSError:
                    size = 0
                skipped.append({
                    "path": filepath,
                    "filename": filename,
                    "size_mb": size / (1024 * 1024),
                    "reason": exclude_reason
                })
                continue

            try:
                stat = os.stat(filepath)
                file_size = stat.st_size
                file_mtime = stat.st_mtime

                # Check cache - reuse MD5 if file unchanged
                md5 = None
                if cache and rel_path in cache:
                    cached = cache[rel_path]
                    if (cached.get("size") == file_size and
                        cached.get("mtime") == file_mtime):
                        md5 = cached.get("md5")

                # Compute MD5 if not cached
                if md5 is None:
                    md5 = compute_md5(filepath)

                file_info = FileInfo(
                    relative_path=rel_path,
                    md5=md5,
                    mtime=file_mtime,
                    size=file_size
                )
                index.add(file_info)

            except (OSError, IOError) as e:
                skipped.append({
                    "path": filepath,
                    "filename": filename,
                    "size_mb": 0,
                    "reason": f"Error reading file: {e}"
                })

    return index, skipped


def load_index_cache(cache_path: str) -> Optional[Dict]:
    """
    Load cached index from JSON file.
    Returns dict of {relative_path: {md5, mtime, size}} or None if not found/invalid.
    """
    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Validate version
        if data.get("version") != INDEX_VERSION:
            return None

        return data.get("files", {})
    except (OSError, json.JSONDecodeError):
        return None


def save_index_cache(cache_path: str, index: FileIndex):
    """Save index to JSON cache file."""
    data = {
        "version": INDEX_VERSION,
        "created": datetime.now().isoformat(),
        "files": {}
    }

    for file_info in index.all_files():
        data["files"][file_info.relative_path] = {
            "md5": file_info.md5,
            "mtime": file_info.mtime,
            "size": file_info.size
        }

    # Write atomically by writing to temp file first
    temp_path = cache_path + ".tmp"
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    # Rename temp to final (atomic on most systems)
    os.replace(temp_path, cache_path)


def get_cache_path(dst_root: str) -> str:
    """Get the path for the index cache file in destination root."""
    return os.path.join(dst_root, INDEX_CACHE_FILENAME)
