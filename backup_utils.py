"""
Backup manager for DevBackupBuddy.
Uses MD5-based indexing for smart sync with move detection.
"""
import os
import sys
from typing import List, Dict, Set
from config import EXCLUDE_DIRS, EXCLUDE_EXTENSIONS, MAX_FILE_SIZE_MB
from file_index import (
    FileIndex, FileInfo, build_index,
    load_index_cache, save_index_cache, get_cache_path
)
from sync_engine import (
    generate_sync_plan, execute_sync_plan, verify_mirror,
    execute_deletes, cleanup_empty_dirs, print_sync_plan_summary,
    SyncPlan, SyncResult
)
from onedrive_utils import is_onedrive_file


class BackupManager:
    """
    Manages backup operations with smart sync capabilities.

    Features:
    - MD5-based file indexing for detecting moved files
    - Cached indexes for faster subsequent backups
    - Safe deletion only after verification
    - Move detection to avoid re-copying reorganized files
    """

    def __init__(self, max_file_size_mb: int = None):
        self.excluded_dirs = set(EXCLUDE_DIRS)
        self.excluded_extensions = set(EXCLUDE_EXTENSIONS)
        self.max_file_size_mb = max_file_size_mb or MAX_FILE_SIZE_MB
        self.skipped_files: List[Dict] = []

    def _format_size(self, size_bytes: int) -> str:
        """Format file size for display."""
        size_mb = size_bytes / (1024 * 1024)
        if size_mb < 1:
            return f"{size_bytes / 1024:.0f}KB"
        if size_mb < 1024:
            return f"{size_mb:.1f}MB"
        return f"{size_mb / 1024:.1f}GB"

    def _progress_callback(self, current: int, total: int, filepath: str):
        """Progress callback for indexing."""
        pct = (current / total * 100) if total > 0 else 0
        # Truncate filepath for display
        display_path = filepath[:50] + "..." if len(filepath) > 50 else filepath
        sys.stdout.write(f"\r  Indexing: {pct:5.1f}% ({current}/{total}) {display_path:<55}")
        sys.stdout.flush()

    def _sync_progress_callback(self, action: str, item, current: int, total: int):
        """Progress callback for sync operations."""
        pct = (current / total * 100) if total > 0 else 0
        display_path = item.src_rel_path or item.dst_rel_path
        if len(display_path) > 45:
            display_path = display_path[:45] + "..."
        sys.stdout.write(f"\r  {action.upper():6} {pct:5.1f}% ({current}/{total}) {display_path:<50}")
        sys.stdout.flush()

    def _verify_progress_callback(self, current: int, total: int, filepath: str):
        """Progress callback for verification."""
        pct = (current / total * 100) if total > 0 else 0
        display_path = filepath[:50] + "..." if len(filepath) > 50 else filepath
        sys.stdout.write(f"\r  Verifying: {pct:5.1f}% ({current}/{total}) {display_path:<50}")
        sys.stdout.flush()

    def backup_directory(self, src: str, dst: str, dry_run: bool = False, verify_only: bool = False):
        """
        Backup source directory to destination with smart sync.

        Args:
            src: Source directory path
            dst: Destination directory path
            dry_run: If True, show what would happen without executing
            verify_only: If True, only verify existing backup without syncing
        """
        src = os.path.abspath(src)
        dst = os.path.abspath(dst)

        if not os.path.exists(src):
            print(f"Source does not exist: {src}")
            return

        # Ensure destination exists
        if not dry_run and not verify_only:
            os.makedirs(dst, exist_ok=True)

        print(f"\n{'=' * 70}")
        print(f"{'DRY RUN - ' if dry_run else ''}DevBackupBuddy Smart Sync")
        print(f"{'=' * 70}")
        print(f"Source:      {src}")
        print(f"Destination: {dst}")
        print(f"Max file size: {self.max_file_size_mb}MB")
        print(f"Excluded dirs: {', '.join(sorted(self.excluded_dirs))}")
        print(f"{'-' * 70}")

        # Phase 1: Build source index
        print("\n[Phase 1] Building source index...")
        src_index, src_skipped = build_index(
            src,
            excluded_dirs=self.excluded_dirs,
            excluded_extensions=self.excluded_extensions,
            max_file_size_mb=self.max_file_size_mb,
            progress_callback=self._progress_callback
        )
        print(f"\n  Source: {len(src_index)} files indexed, {len(src_skipped)} skipped")
        self.skipped_files = src_skipped

        # If verify_only, just verify and exit
        if verify_only:
            print("\n[Verify Only Mode] Checking destination...")
            success, mismatches = verify_mirror(
                src_index, dst,
                progress_callback=self._verify_progress_callback
            )
            print()
            self._print_verification_result(success, mismatches)
            return

        # Phase 2: Build destination index (with cache)
        print("\n[Phase 2] Building destination index...")
        cache_path = get_cache_path(dst)
        dst_cache = load_index_cache(cache_path) if os.path.exists(cache_path) else None
        if dst_cache:
            print(f"  Using cached index ({len(dst_cache)} entries)")

        dst_index, _ = build_index(
            dst,
            excluded_dirs=self.excluded_dirs,
            excluded_extensions=self.excluded_extensions,
            max_file_size_mb=999999,  # Don't skip large files in destination
            cache=dst_cache,
            progress_callback=self._progress_callback
        )
        print(f"\n  Destination: {len(dst_index)} files indexed")

        # Phase 3: Generate sync plan
        print("\n[Phase 3] Generating sync plan...")
        plan = generate_sync_plan(src_index, dst_index, src, dst)
        print_sync_plan_summary(plan)

        # Nothing to do?
        if not plan.copies and not plan.moves and not plan.deletes:
            print("Destination is already in sync!")
            self._print_summary(0, 0, 0, len(plan.skips))
            return

        if dry_run:
            print("\n[DRY RUN] No changes made.")
            self._print_summary(
                len(plan.copies), len(plan.moves), len(plan.deletes),
                len(plan.skips), dry_run=True
            )
            return

        # Phase 4: Execute sync (moves + copies)
        print("\n[Phase 4] Executing sync...")
        result = execute_sync_plan(
            plan,
            dry_run=dry_run,
            progress_callback=self._sync_progress_callback
        )
        print()

        if result.errors:
            print(f"\n  Errors during sync:")
            for err in result.errors[:10]:
                print(f"    {err['action']}: {err['path']} - {err['error']}")
            if len(result.errors) > 10:
                print(f"    ... and {len(result.errors) - 10} more errors")

        # Phase 5: Verify mirror integrity
        print("\n[Phase 5] Verifying mirror integrity...")
        success, mismatches = verify_mirror(
            src_index, dst,
            progress_callback=self._verify_progress_callback
        )
        print()

        if not success:
            print(f"\n  VERIFICATION FAILED - {len(mismatches)} mismatches found:")
            for m in mismatches[:10]:
                print(f"    {m['path']}: {m['reason']}")
            if len(mismatches) > 10:
                print(f"    ... and {len(mismatches) - 10} more")
            print("\n  Skipping deletions due to verification failure.")
            self._print_summary(result.copied, result.moved, 0, result.skipped)
            return

        print("  Verification PASSED!")

        # Phase 6: Execute deletions (only after verification)
        deleted = 0
        if plan.deletes:
            print(f"\n[Phase 6] Deleting {len(plan.deletes)} orphaned files...")
            deleted, del_errors = execute_deletes(plan, dry_run=dry_run)
            if del_errors:
                print(f"  Errors during deletion:")
                for err in del_errors[:5]:
                    print(f"    {err['path']}: {err['error']}")

        # Phase 7: Clean up empty directories
        print("\n[Phase 7] Cleaning empty directories...")
        removed_dirs = cleanup_empty_dirs(dst, dry_run=dry_run)
        if removed_dirs:
            print(f"  Removed {removed_dirs} empty directories")

        # Phase 8: Save updated index cache
        print("\n[Phase 8] Saving index cache...")
        # Rebuild destination index after all changes
        final_dst_index, _ = build_index(
            dst,
            excluded_dirs=self.excluded_dirs,
            excluded_extensions=self.excluded_extensions,
            max_file_size_mb=999999,
            progress_callback=None  # Silent rebuild
        )
        save_index_cache(cache_path, final_dst_index)
        print(f"  Cache saved: {cache_path}")

        # Print final summary
        self._print_summary(result.copied, result.moved, deleted, result.skipped)
        self._print_skipped_files()

    def _print_verification_result(self, success: bool, mismatches: List[Dict]):
        """Print verification results."""
        print(f"\n{'=' * 70}")
        if success:
            print("VERIFICATION PASSED - Destination is a valid mirror")
        else:
            print(f"VERIFICATION FAILED - {len(mismatches)} issues found:")
            for m in mismatches[:20]:
                print(f"  {m['path']}: {m['reason']}")
            if len(mismatches) > 20:
                print(f"  ... and {len(mismatches) - 20} more")
        print(f"{'=' * 70}")

    def _print_summary(self, copied: int, moved: int, deleted: int, skipped: int, dry_run: bool = False):
        """Print backup summary."""
        print(f"\n{'=' * 70}")
        print(f"{'DRY RUN ' if dry_run else ''}Backup Complete!")
        print(f"{'=' * 70}")
        print(f"  Files copied:  {copied}")
        print(f"  Files moved:   {moved}")
        print(f"  Files deleted: {deleted}")
        print(f"  Files skipped: {skipped}")
        print(f"{'=' * 70}")

    def _print_skipped_files(self):
        """Print skipped files summary."""
        if not self.skipped_files:
            return

        print(f"\nSkipped files ({len(self.skipped_files)} total):")
        print(f"{'File':<50} | {'Size':<10} | Reason")
        print("-" * 90)

        # Sort by size descending
        sorted_skipped = sorted(self.skipped_files, key=lambda x: x["size_mb"], reverse=True)
        for item in sorted_skipped[:20]:
            filename = item['filename'][:48]
            size = self._format_size(int(item['size_mb'] * 1024 * 1024))
            print(f"{filename:<50} | {size:<10} | {item['reason']}")

        if len(sorted_skipped) > 20:
            print(f"... and {len(sorted_skipped) - 20} more skipped files")
