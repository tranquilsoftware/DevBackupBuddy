# DevBackupBuddy

Smart backup utility with **MD5-based move detection**. When you reorganize files in your source folder, it moves them on the backup instead of re-copying. Verifies integrity before deleting orphaned files.

## Quick Start

```bash
python main.py backup "C:/Projects" -d "E:/Backup"           # Normal backup
python main.py backup "C:/Projects" -d "E:/Backup" --dry-run # Preview changes
python main.py backup "C:/Projects" -d "E:/Backup" --verify-only # Verify integrity
python main.py list                                          # List available drives
```

## Features

- **Move detection** - Reorganized files are moved, not re-copied (via MD5 matching)
- **Cached indexes** - MD5 hashes cached in `.backup_index.json` for faster subsequent backups
- **Safe deletion** - Orphaned files only deleted after full verification passes
- **Dry run mode** - See what would happen without making changes
- **Smart exclusions** - Skips `node_modules`, `.git`, `__pycache__`, etc.

## How It Works

1. **Index source** - Compute MD5, size, mtime for each file
2. **Index destination** - Load from cache or compute (reuses cached MD5 if file unchanged)
3. **Generate plan** - Compare indexes, detect moves via MD5 + filename matching
4. **Execute** - Move files, then copy new/changed files
5. **Verify** - Confirm destination mirrors source correctly
6. **Delete** - Remove orphaned files only after verification passes
7. **Cache** - Save updated index for next run

## File Structure

| File | Purpose |
|------|---------|
| `main.py` | CLI entry point |
| `backup_utils.py` | BackupManager orchestrates the 8-phase sync |
| `file_index.py` | FileInfo/FileIndex classes, MD5 computation, JSON caching |
| `sync_engine.py` | Plan generation, execution, verification, deletion |
| `config.py` | Exclusion lists, max file size setting |
| `disk_utils.py` | Drive detection utilities |

## CLI Options

```
python main.py backup <source> -d <destination> [options]

Options:
  --dry-run        Show what would happen without making changes
  --verify-only    Only verify existing backup, don't sync
  --max-file-size  Skip files larger than N MB (default: 256)
```

## Default Exclusions

Directories: `node_modules`, `dist`, `build`, `.git`, `__pycache__`, `.venv`, `venv`, `.idea`, `.vscode`, `libs`

Extensions: `.tmp`, `.log`, `.pyc`, `.pyo`, `.pyd`, `.DS_Store`

Edit `config.py` to customize.

## Example Output

```
======================================================================
DevBackupBuddy Smart Sync
======================================================================
Source:      C:/Projects
Destination: E:/Backup
----------------------------------------------------------------------

[Phase 1] Building source index...
  Source: 1542 files indexed, 23 skipped

[Phase 2] Building destination index...
  Using cached index (1538 entries)
  Destination: 1538 files indexed

[Phase 3] Generating sync plan...
Sync Plan Summary:
  Files to skip (up-to-date): 1520
  Files to copy: 15
  Files to move: 7
  Files to delete: 3

[Phase 4] Executing sync...
[Phase 5] Verifying mirror integrity...
  Verification PASSED!
[Phase 6] Deleting 3 orphaned files...
[Phase 7] Cleaning empty directories...
[Phase 8] Saving index cache...

======================================================================
Backup Complete!
======================================================================
  Files copied:  15
  Files moved:   7
  Files deleted: 3
  Files skipped: 1520
======================================================================
```

## License

Free Forever. Tranquil Software certified.
