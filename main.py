"""
Command-line backup utility for backing up directories to external drives.

How to Use:

1. List available backup destinations:
   python main.py list

2. Start a backup:
   python main.py backup <source> --destination <drive_letter>/<folder>
   e.g.: `python main.py backup "C:/path/to/source" --destination "D:/backups" --name "my_backup"`
   e.g.: `python main.py backup "C:/Users/username/OneDrive/TranquilSoftware" --destination "D:/backups" --name "TranquilSoftware"` 
        --> Saves C:/Users/username/OneDrive/TranquilSoftware to D:/backups/TranquilSoftware

3. Configure backup settings:
   python main.py config --add-exclude <directory>
   python main.py config --remove-exclude <directory>
   python main.py config --list-excludes
"""
import argparse
import os
from backup_utils import BackupManager
from disk_utils import get_available_drives, is_valid_destination
from config import MAX_FILE_SIZE_MB

def main():
    parser = argparse.ArgumentParser(description="Developer Backup Buddy")
    subparsers = parser.add_subparsers(dest="command")

    # List available drives
    subparsers.add_parser("list", help="List available backup destinations")

    # Backup command
    backup_parser = subparsers.add_parser("backup", help="Backup a directory")
    backup_parser.add_argument("source", help="Source directory")
    backup_parser.add_argument("--destination", "-d", required=True, help="Destination directory")
    backup_parser.add_argument("--max-file-size", type=int, help="Override max file size in MB")

    args = parser.parse_args()

    if args.command == "list":
        drives = get_available_drives()
        print("Available drives:", drives)
        return

    if args.command == "backup":
        src = args.source
        dst = args.destination

        if not os.path.exists(src):
            print("Source directory does not exist!")
            return
        if not os.path.exists(dst) or not is_valid_destination(dst):
            print("Destination is invalid or not writable!")
            return

        max_size = args.max_file_size if args.max_file_size else MAX_FILE_SIZE_MB
        manager = BackupManager(max_file_size_mb=max_size)
        manager.backup_directory(src, dst)

if __name__ == "__main__":
    main()