"""
Configuration settings for the backup script.
"""

# Maximum file size in MB (files larger than this will be skipped)
MAX_FILE_SIZE_MB = 256

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

# Project templates for multi-project file handling
# Files in 'always_copy' will never be treated as "moves" across different projects
# This prevents identical boilerplate files from being incorrectly detected as moved
PROJECT_TEMPLATES = {
    'nodejs': {
        'marker_files': ['package.json'],
        'always_copy': [
            '.gitignore',
            '.npmrc',
            '.nvmrc',
            '.node-version',
            'package-lock.json',
            'yarn.lock',
            'pnpm-lock.yaml',
        ],
    },
    'typescript': {
        'marker_files': ['tsconfig.json'],
        'always_copy': [
            'tsconfig.json',
            'tsconfig.app.json',
            'tsconfig.node.json',
            'tsconfig.build.json',
        ],
    },
    'vite': {
        'marker_files': ['vite.config.ts', 'vite.config.js'],
        'always_copy': [
            'vite.config.ts',
            'vite.config.js',
            'postcss.config.js',
            'postcss.config.cjs',
            'tailwind.config.js',
            'tailwind.config.ts',
            'index.html',
        ],
    },
    'react': {
        'marker_files': ['src/App.tsx', 'src/App.jsx', 'src/main.tsx', 'src/main.jsx'],
        'always_copy': [
            'src/App.tsx',
            'src/App.jsx',
            'src/main.tsx',
            'src/main.jsx',
            'src/index.css',
            'src/App.css',
            'src/vite-env.d.ts',
        ],
    },
    'swc': {
        'marker_files': ['.swcrc'],
        'always_copy': [
            '.swcrc',
        ],
    },
    'eslint': {
        'marker_files': ['eslint.config.js', 'eslint.config.mjs', '.eslintrc.js', '.eslintrc.json', '.eslintrc.cjs'],
        'always_copy': [
            'eslint.config.js',
            'eslint.config.mjs',
            '.eslintrc.js',
            '.eslintrc.json',
            '.eslintrc.cjs',
            '.prettierrc',
            '.prettierrc.json',
            '.prettierrc.js',
            '.editorconfig',
        ],
    },
    'jest': {
        'marker_files': ['jest.config.js', 'jest.config.ts', 'jest.config.mjs'],
        'always_copy': [
            'jest.config.js',
            'jest.config.ts',
            'jest.config.mjs',
            'jest.setup.js',
            'jest.setup.ts',
        ],
    },
    'pwa': {
        # PWA/favicon files are detected by site.webmanifest or favicon folder
        'marker_files': ['public/favicon/site.webmanifest', 'public/site.webmanifest', 'public/manifest.json'],
        'always_copy': [
            'public/favicon/site.webmanifest',
            'public/favicon/favicon.ico',
            'public/favicon/favicon-16x16.png',
            'public/favicon/favicon-32x32.png',
            'public/favicon/apple-touch-icon.png',
            'public/favicon/android-chrome-192x192.png',
            'public/favicon/android-chrome-512x512.png',
            'public/site.webmanifest',
            'public/manifest.json',
            'public/favicon.ico',
        ],
    },
    'shadcn': {
        # shadcn/ui projects have src/lib/utils.ts and components.json
        'marker_files': ['components.json', 'src/lib/utils.ts'],
        'always_copy': [
            'src/lib/utils.ts',
            'components.json',
            'src/components/ui/button.tsx',
            'src/components/ui/input.tsx',
            'src/components/ui/card.tsx',
        ],
    },
    'python': {
        'marker_files': ['pyproject.toml', 'setup.py', 'requirements.txt'],
        'always_copy': [
            'pyproject.toml',
            'setup.py',
            'setup.cfg',
            'requirements.txt',
            'requirements-dev.txt',
            '.python-version',
            'pytest.ini',
            'conftest.py',
            'tox.ini',
        ],
    },
    'git': {
        'marker_files': ['.git'],
        'always_copy': [
            '.gitignore',
            '.gitattributes',
            'LICENSE',
            'LICENSE.md',
            'LICENSE.txt',
            'README.md',
            'CHANGELOG.md',
        ],
    },
}