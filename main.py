"""
Command-line backup utility for backing up directories to external drives.

How to Use:

1. List available backup destinations:
   python main.py list

2. Start a backup:
   python main.py backup <source> --destination <drive_letter>\\<folder>
   e.g.: `python main.py backup "C:/path/to/source" --destination "D:/backups" --name "my_backup"`
   e.g.: `python main.py backup "C:/Users/username/OneDrive/TranquilSoftware" --destination "D:/backups" --name "TranquilSoftware"` 
        \--> Saves C:/Users/username/OneDrive/TranquilSoftware to D:/backups/TranquilSoftware

3. Configure backup settings:
   python main.py config --add-exclude <directory>
   python main.py config --remove-exclude <directory>
   python main.py config --list-excludes
"""
import os
import sys
import argparse
from typing import List, Optional
from pathlib import Path

from disk_utils import get_available_drives, is_valid_destination, create_backup_directory
from backup_utils import BackupManager
from config import EXCLUDE_DIRS, EXCLUDE_EXTENSIONS

class BackupCLI:
    def __init__(self):
        self.backup_manager = BackupManager()
        self.parser = self._create_parser()
    
    def _create_parser(self) -> argparse.ArgumentParser:
        """Create the command line argument parser."""
        parser = argparse.ArgumentParser(description='Backup utility for directories')
        subparsers = parser.add_subparsers(dest='command', help='Commands')
        
        # List command
        list_parser = subparsers.add_parser('list', help='List available backup destinations')
        
        # Backup command
        backup_parser = subparsers.add_parser('backup', help='Start a backup')
        backup_parser.add_argument('source', help='Source directory to back up')
        backup_parser.add_argument('--destination', help='Destination directory (optional)')
        backup_parser.add_argument('--name', default='backup', help='Backup directory name (default: backup)')
        
        # Config command
        config_parser = subparsers.add_parser('config', help='Configure backup settings')
        config_parser.add_argument('--add-exclude', help='Add directory to exclude list')
        config_parser.add_argument('--remove-exclude', help='Remove directory from exclude list')
        config_parser.add_argument('--list-excludes', action='store_true', help='List all excluded directories')
        
        return parser
    
    def list_destinations(self) -> None:
        """List all available backup destinations."""
        print("\nAvailable backup destinations:")
        print("-" * 40)
        
        drives = get_available_drives()
        if not drives:
            print("No external drives found. Please connect a USB drive and try again.")
            return
        
        for i, drive in enumerate(drives, 1):
            print(f"{i}. {drive}")
        
        print("\nTo start a backup, run:")
        print("  python main.py backup <source> --destination <drive_letter>\\<folder>")
    
    def run_backup(self, source: str, destination: Optional[str] = None, name: str = 'backup') -> None:
        """Run the backup process."""
        if not os.path.exists(source):
            print(f"Error: Source directory does not exist: {source}")
            return
        
        if not destination:
            # If no destination specified, show available drives
            self.list_destinations()
            return
        
        if not is_valid_destination(destination):
            print(f"Error: Cannot write to destination: {destination}")
            return
        
        # Create backup directory with timestamp
        backup_path = create_backup_directory(destination, name)
        
        # Start the backup
        self.backup_manager.backup_directory(source, backup_path)
    
    def update_config(self, args) -> None:
        """Update configuration settings."""
        if args.list_excludes:
            print("\nExcluded directories:")
            print("-" * 40)
            for item in sorted(EXCLUDE_DIRS):
                print(f"- {item}")
            return
        
        if args.add_exclude:
            if args.add_exclude not in EXCLUDE_DIRS:
                EXCLUDE_DIRS.append(args.add_exclude)
                self._save_config()
                print(f"Added '{args.add_exclude}' to exclude list")
            else:
                print(f"'{args.add_exclude}' is already in the exclude list")
        
        if args.remove_exclude:
            if args.remove_exclude in EXCLUDE_DIRS:
                EXCLUDE_DIRS.remove(args.remove_exclude)
                self._save_config()
                print(f"Removed '{args.remove_exclude}' from exclude list")
            else:
                print(f"'{args.remove_exclude}' is not in the exclude list")
    
    def _save_config(self) -> None:
        """Save the current configuration to config.py."""
        with open('config.py', 'w') as f:
            f.write('"""\nConfiguration settings for the backup script.\n"""\
\n')
            f.write('# List of directories to exclude from backup\n')
            f.write('EXCLUDE_DIRS = [\n')
            for item in sorted(EXCLUDE_DIRS):
                f.write(f'    \'{item}\',\n')
            f.write(']\n\n')
            f.write('# File extensions to exclude (optional)\n')
            f.write('EXCLUDE_EXTENSIONS = [\n')
            for ext in sorted(EXCLUDE_EXTENSIONS):
                f.write(f'    \'{ext}\',\n')
            f.write(']\n')
    
    def run(self) -> None:
        """Run the CLI application."""
        if len(sys.argv) == 1:
            self.parser.print_help()
            return
        
        args = self.parser.parse_args()
        
        if args.command == 'list':
            self.list_destinations()
        elif args.command == 'backup':
            self.run_backup(args.source, args.destination, args.name)
        elif args.command == 'config':
            self.update_config(args)
        else:
            self.parser.print_help()


def main():
    """Main entry point for the backup script."""
    try:
        cli = BackupCLI()
        cli.run()
    except KeyboardInterrupt:
        print("\nBackup cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\nAn error occurred: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
