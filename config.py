"""
Configuration settings for the backup script.
"""

# List of directories to exclude from backup
EXCLUDE_DIRS = [
    # typescript / web dev
    'node_modules',
    'dist',

    # c++
    'build',
    'libs',

    # python
    '__pycache__',
    '.venv',
    'venv',

    # git
    '.git',
    
    # IDE
    '.idea',
    '.vscode',
]

# File extensions to exclude (optional)
EXCLUDE_EXTENSIONS = [
    '.tmp',
    '.log',
    '.pyc',
    '.pyo',
    '.pyd',
    '.DS_Store'
]

# Maximum file size in MB (files larger than this will be skipped)
MAX_FILE_SIZE_MB = 256
