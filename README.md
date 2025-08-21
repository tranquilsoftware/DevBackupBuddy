## DevBackupBuddy
# Development Backup Utility

A simple command-line utility for backing up directories to external drives with smart exclusions.

## Features

- 🔍 Automatic detection of available drives
- 🚫 Smart exclusion of common development directories (`node_modules`, `dist/`, `.git`, etc.)
- ⚙️ Configurable exclude list
- 📂 Preserves directory structure
- 🖥️ Simple CLI interface

## Installation

1. Clone this repository
2. Install Python 3.8+
3. No additional dependencies required!

## Usage

```bash
# List available backup destinations
python main.py list

# Run a backup -- Saves `C:/path/to/source` to `D:/backups/my_backup`
python main.py backup "C:/path/to/source" --destination "D:/backups" --name "my_backup" 

# Run a backup with a custom max file size (Dont save files > 512MB)
python main.py backup "C:/path/to/source" --destination "D:/backups" --name "my_backup" --max-file-size 512

# Manage excluded directories
python main.py config --list-excludes
python main.py config --add-exclude "temp"
python main.py config --remove-exclude "temp"
```

## Default Exclusions

To add/remove a directory, simply go to the config.py file and modify to your development needs.

- Temporary files: `.tmp`, `.log`, `.pyc`, `.pyo`, `.pyd`, `.DS_Store`
 
- Development directories:
- `node_modules/` - Node.js dependencies
- `build/` - Build output directories
- `dist/` - Distribution directories
- `.git/` - Git repository data
- `__pycache__/` - Python cache
- `.venv/`, `venv/` - Python virtual environments
- `.idea/`, `.vscode/` - IDE settings

## Skipped Files

When running a backup, certain files and directories are automatically skipped based on your configuration. The backup tool provides a detailed report of skipped items, including the reason for exclusion. This helps you understand what was excluded and why.

### Example Output
==================================================
Backup completed!
Total files processed: 2216
Files skipped: 41
Files copied: 2175
==================================================
Skipped files:
----------------------------------------------------------------------------------------------------
File                                             | Size           | Reason
----------------------------------------------------------------------------------------------------
background.psd                                   | 293.3MB        | File size: 293.3MB > 256MB
app.log                                         | 1.2MB          | Excluded extension: .log
node_modules/                                    | 0B             | Excluded directory: node_modules
==================================================

## License

Free Forever. Tranquil Software certified.


