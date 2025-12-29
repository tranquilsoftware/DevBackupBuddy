"""
Command-line backup utility for backing up directories to external drives.

DevBackupBuddy - Smart sync with move detection.

How to Use:

1. List available backup destinations:
   python main.py list

2. Start a backup:
   python main.py backup <source> --destination <drive_letter>/<folder>
   e.g.: `python main.py backup "C:/path/to/source" --destination "D:/backups"`

3. Dry run (see what would happen without making changes):
   python main.py backup "C:/path/to/source" --destination "D:/backups" --dry-run

4. Verify an existing backup:
   python main.py backup "C:/path/to/source" --destination "D:/backups" --verify-only

5. Configure backup settings:
   python main.py config --list-excludes

Features:
- MD5-based file indexing for detecting moved/reorganized files
- Moves files on destination instead of re-copying when reorganized
- Cached indexes for faster subsequent backups
- Safe deletion only after full verification
"""
import argparse
import os
from backup_utils import BackupManager
from disk_utils import get_available_drives, is_valid_destination
from config import MAX_FILE_SIZE_MB


def main():
    parser = argparse.ArgumentParser(
        description="DevBackupBuddy - Smart directory backup with move detection",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py list
  python main.py backup "C:/Projects" -d "E:/Backups"
  python main.py backup "C:/Projects" -d "E:/Backups" --dry-run
  python main.py backup "C:/Projects" -d "E:/Backups" --verify-only
        """
    )
    subparsers = parser.add_subparsers(dest="command")

    # List available drives
    subparsers.add_parser("list", help="List available backup destinations")

    # Backup command
    backup_parser = subparsers.add_parser("backup", help="Backup a directory")
    backup_parser.add_argument("source", help="Source directory to backup")
    backup_parser.add_argument(
        "--destination", "-d",
        required=True,
        help="Destination directory for backup"
    )
    backup_parser.add_argument(
        "--max-file-size",
        type=int,
        default=MAX_FILE_SIZE_MB,
        help=f"Maximum file size in MB (default: {MAX_FILE_SIZE_MB})"
    )
    backup_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would happen without making changes"
    )
    backup_parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Only verify existing backup, don't sync"
    )

    args = parser.parse_args()

    if args.command == "list":
        drives = get_available_drives()
        print("Available drives for backup:")
        for drive in drives:
            print(f"  {drive}")
        if not drives:
            print("  No external drives detected")
        return

    if args.command == "backup":
        src = args.source
        dst = args.destination

        if not os.path.exists(src):
            print(f"Error: Source directory does not exist: {src}")
            return

        # For dry-run or verify-only, destination doesn't need to be writable
        if not args.dry_run and not args.verify_only:
            if not os.path.exists(dst):
                # Try to create it
                try:
                    os.makedirs(dst, exist_ok=True)
                except OSError as e:
                    print(f"Error: Cannot create destination directory: {e}")
                    return

            if not is_valid_destination(dst):
                print(f"Error: Destination is not writable: {dst}")
                return

        manager = BackupManager(max_file_size_mb=args.max_file_size)
        manager.backup_directory(
            src, dst,
            dry_run=args.dry_run,
            verify_only=args.verify_only
        )
        return

    # No command specified
    parser.print_help()


if __name__ == "__main__":
    main()
