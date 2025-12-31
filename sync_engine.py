"""
Sync engine for DevBackupBuddy.
Generates and executes sync plans with move detection and safe deletion.
"""
import os
import shutil
from enum import Enum
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple, Set
from file_index import FileIndex, FileInfo, compute_md5, normalize_path
from config import PROJECT_TEMPLATES


class SyncAction(Enum):
    """Types of sync actions."""
    SKIP = "skip"           # File already up-to-date
    COPY = "copy"           # Copy new or updated file
    MOVE = "move"           # Move file to new location (reorganization detected)
    DELETE = "delete"       # Delete file not in source (after verification)


@dataclass
class SyncItem:
    """A single sync action to perform."""
    action: SyncAction
    src_path: Optional[str]    # Source file path (None for DELETE)
    dst_path: str              # Destination file path
    src_rel_path: Optional[str]  # Source relative path
    dst_rel_path: str          # Destination relative path
    move_from: Optional[str] = None  # For MOVE: original location on destination
    reason: str = ""           # Human-readable reason for action


@dataclass
class SyncPlan:
    """Complete sync plan with all actions."""
    items: List[SyncItem]
    src_root: str
    dst_root: str

    @property
    def skips(self) -> List[SyncItem]:
        return [i for i in self.items if i.action == SyncAction.SKIP]

    @property
    def copies(self) -> List[SyncItem]:
        return [i for i in self.items if i.action == SyncAction.COPY]

    @property
    def moves(self) -> List[SyncItem]:
        return [i for i in self.items if i.action == SyncAction.MOVE]

    @property
    def deletes(self) -> List[SyncItem]:
        return [i for i in self.items if i.action == SyncAction.DELETE]


def _find_best_move_candidate(
    src_file: FileInfo,
    dst_candidates: List[FileInfo],
    src_root: str,
    dst_root: str
) -> Optional[FileInfo]:
    """
    Find the best destination file to move from among candidates with same MD5.
    Priority: 1) Same filename, 2) Shortest path distance
    """
    if not dst_candidates:
        return None

    src_filename = os.path.basename(src_file.relative_path)

    # First, try to find a candidate with the same filename
    same_name = [c for c in dst_candidates if os.path.basename(c.relative_path) == src_filename]
    if same_name:
        # If multiple with same name, pick shortest path distance
        return min(same_name, key=lambda c: _path_distance(src_file.relative_path, c.relative_path))

    # Otherwise, pick the one with shortest path distance
    return min(dst_candidates, key=lambda c: _path_distance(src_file.relative_path, c.relative_path))


def _path_distance(path1: str, path2: str) -> int:
    """Calculate a simple distance metric between two paths."""
    parts1 = path1.split("/")
    parts2 = path2.split("/")

    # Count differing directory levels
    common_prefix_len = 0
    for p1, p2 in zip(parts1[:-1], parts2[:-1]):
        if p1 == p2:
            common_prefix_len += 1
        else:
            break

    return (len(parts1) - 1 - common_prefix_len) + (len(parts2) - 1 - common_prefix_len)


def detect_project_roots(src_index: FileIndex) -> Dict[str, Set[str]]:
    """
    Detect project roots by looking for marker files.
    
    Returns:
        Dict mapping project_path (e.g., 'my-app') to set of detected project types
    """
    project_roots: Dict[str, Set[str]] = {}
    
    for file_info in src_index.all_files():
        filename = os.path.basename(file_info.relative_path)
        
        for project_type, template in PROJECT_TEMPLATES.items():
            for marker in template['marker_files']:
                # Handle markers that include subdirectories (e.g., 'src/App.tsx')
                if '/' in marker:
                    if file_info.relative_path.endswith(marker):
                        # Get project root by removing the marker path
                        marker_depth = marker.count('/') + 1
                        parts = file_info.relative_path.split('/')
                        if len(parts) > marker_depth:
                            project_root = '/'.join(parts[:-marker_depth])
                        else:
                            project_root = ''
                        
                        if project_root not in project_roots:
                            project_roots[project_root] = set()
                        project_roots[project_root].add(project_type)
                else:
                    # Simple filename marker
                    if filename == marker:
                        # Get the directory containing this file as the project root
                        parts = file_info.relative_path.split('/')
                        if len(parts) > 1:
                            project_root = '/'.join(parts[:-1])
                        else:
                            project_root = ''
                        
                        if project_root not in project_roots:
                            project_roots[project_root] = set()
                        project_roots[project_root].add(project_type)
    
    return project_roots


def build_always_copy_map(project_roots: Dict[str, Set[str]]) -> Dict[str, Set[str]]:
    """
    Build a map of file paths that should always be copied (never moved across projects).
    
    Returns:
        Dict mapping relative file path to set of project roots it belongs to
    """
    always_copy_map: Dict[str, Set[str]] = {}
    
    for project_root, project_types in project_roots.items():
        for project_type in project_types:
            template = PROJECT_TEMPLATES.get(project_type, {})
            for filename in template.get('always_copy', []):
                if project_root:
                    file_path = f"{project_root}/{filename}"
                else:
                    file_path = filename
                
                if file_path not in always_copy_map:
                    always_copy_map[file_path] = set()
                always_copy_map[file_path].add(project_root)
    
    return always_copy_map


def get_project_root(file_path: str, project_roots: Dict[str, Set[str]]) -> Optional[str]:
    """
    Get the project root that a file belongs to.
    Returns the longest matching project root, or None if not in a detected project.
    """
    parts = file_path.split('/')
    
    # Try progressively shorter paths to find the project root
    for i in range(len(parts) - 1, -1, -1):
        candidate = '/'.join(parts[:i]) if i > 0 else ''
        if candidate in project_roots:
            return candidate
    
    return None


def is_cross_project_move(
    src_path: str,
    candidate_path: str,
    project_roots: Dict[str, Set[str]],
    always_copy_map: Dict[str, Set[str]]
) -> bool:
    """
    Check if a potential move is actually a cross-project copy of a boilerplate file.
    
    Returns True if this should be treated as COPY instead of MOVE.
    """
    src_filename = os.path.basename(src_path)
    
    # Check if the source file is in the always-copy map
    if src_path in always_copy_map:
        # Get project roots for source and candidate
        src_project = get_project_root(src_path, project_roots)
        candidate_project = get_project_root(candidate_path, project_roots)
        
        # If they're in different projects, don't treat as move
        if src_project != candidate_project:
            return True
    
    return False




def generate_sync_plan(
    src_index: FileIndex,
    dst_index: FileIndex,
    src_root: str,
    dst_root: str
) -> SyncPlan:
    """
    Generate a sync plan by comparing source and destination indexes.

    Returns a SyncPlan with actions: SKIP, COPY, MOVE, DELETE
    """
    items: List[SyncItem] = []

    # Track which destination files are "used" by a move
    used_dst_paths = set()

    # Detect project roots and build always-copy map for smart move detection
    project_roots = detect_project_roots(src_index)
    always_copy_map = build_always_copy_map(project_roots)

    # Process each source file
    for src_file in src_index.all_files():
        src_full = os.path.join(src_root, src_file.relative_path.replace("/", os.sep))
        dst_full = os.path.join(dst_root, src_file.relative_path.replace("/", os.sep))

        # Check if file exists at same path in destination
        dst_file = dst_index.get_by_path(src_file.relative_path)

        if dst_file:
            if dst_file.md5 == src_file.md5:
                # Same path, same content -> SKIP
                items.append(SyncItem(
                    action=SyncAction.SKIP,
                    src_path=src_full,
                    dst_path=dst_full,
                    src_rel_path=src_file.relative_path,
                    dst_rel_path=src_file.relative_path,
                    reason="Up-to-date"
                ))
                used_dst_paths.add(src_file.relative_path)
            else:
                # Same path, different content -> COPY (update)
                items.append(SyncItem(
                    action=SyncAction.COPY,
                    src_path=src_full,
                    dst_path=dst_full,
                    src_rel_path=src_file.relative_path,
                    dst_rel_path=src_file.relative_path,
                    reason="Content changed"
                ))
                used_dst_paths.add(src_file.relative_path)
        else:
            # File doesn't exist at same path - check for move (same MD5 elsewhere)
            candidates = dst_index.get_by_md5(src_file.md5)
            # Filter out already-used candidates
            candidates = [c for c in candidates if c.relative_path not in used_dst_paths]

            move_candidate = _find_best_move_candidate(src_file, candidates, src_root, dst_root)

            # Check if this is a cross-project boilerplate file
            if move_candidate and is_cross_project_move(
                src_file.relative_path,
                move_candidate.relative_path,
                project_roots,
                always_copy_map
            ):
                # This is identical boilerplate across different projects - COPY, not MOVE
                items.append(SyncItem(
                    action=SyncAction.COPY,
                    src_path=src_full,
                    dst_path=dst_full,
                    src_rel_path=src_file.relative_path,
                    dst_rel_path=src_file.relative_path,
                    reason="Project boilerplate (same content in other project)"
                ))
            elif move_candidate:
                # Found file with same content at different location -> MOVE
                move_from = os.path.join(dst_root, move_candidate.relative_path.replace("/", os.sep))
                items.append(SyncItem(
                    action=SyncAction.MOVE,
                    src_path=src_full,
                    dst_path=dst_full,
                    src_rel_path=src_file.relative_path,
                    dst_rel_path=src_file.relative_path,
                    move_from=move_from,
                    reason=f"Moved from {move_candidate.relative_path}"
                ))
                used_dst_paths.add(move_candidate.relative_path)
            else:
                # File not found anywhere in destination -> COPY (new)
                items.append(SyncItem(
                    action=SyncAction.COPY,
                    src_path=src_full,
                    dst_path=dst_full,
                    src_rel_path=src_file.relative_path,
                    dst_rel_path=src_file.relative_path,
                    reason="New file"
                ))

    # Find files in destination that aren't in source (candidates for deletion)
    for dst_file in dst_index.all_files():
        if dst_file.relative_path not in used_dst_paths:
            src_file = src_index.get_by_path(dst_file.relative_path)
            if not src_file:
                # File exists in destination but not source -> DELETE
                dst_full = os.path.join(dst_root, dst_file.relative_path.replace("/", os.sep))
                items.append(SyncItem(
                    action=SyncAction.DELETE,
                    src_path=None,
                    dst_path=dst_full,
                    src_rel_path=None,
                    dst_rel_path=dst_file.relative_path,
                    reason="Not in source"
                ))

    return SyncPlan(items=items, src_root=src_root, dst_root=dst_root)


@dataclass
class SyncResult:
    """Result of sync execution."""
    moved: int = 0
    copied: int = 0
    deleted: int = 0
    skipped: int = 0
    errors: List[Dict] = None
    verification_passed: bool = True

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


def execute_sync_plan(
    plan: SyncPlan,
    dry_run: bool = False,
    progress_callback=None
) -> SyncResult:
    """
    Execute a sync plan.

    Order of operations:
    1. Create directories
    2. Move files
    3. Copy files
    4. (Verification done separately)
    5. Delete files (called separately after verification)

    Args:
        plan: The sync plan to execute
        dry_run: If True, don't actually perform operations
        progress_callback: Optional callback(action, item, current, total)

    Returns:
        SyncResult with counts and any errors
    """
    result = SyncResult()
    total_ops = len(plan.moves) + len(plan.copies)
    current_op = 0

    # Phase 1: Create all needed directories
    needed_dirs = set()
    for item in plan.moves + plan.copies:
        needed_dirs.add(os.path.dirname(item.dst_path))

    if not dry_run:
        for d in needed_dirs:
            os.makedirs(d, exist_ok=True)

    # Phase 2: Execute moves
    for item in plan.moves:
        current_op += 1
        if progress_callback:
            progress_callback("move", item, current_op, total_ops)

        if dry_run:
            result.moved += 1
            continue

        try:
            # Ensure target directory exists
            os.makedirs(os.path.dirname(item.dst_path), exist_ok=True)
            shutil.move(item.move_from, item.dst_path)
            result.moved += 1
        except (OSError, IOError) as e:
            result.errors.append({
                "action": "move",
                "path": item.move_from,
                "target": item.dst_path,
                "error": str(e)
            })

    # Phase 3: Execute copies
    for item in plan.copies:
        current_op += 1
        if progress_callback:
            progress_callback("copy", item, current_op, total_ops)

        if dry_run:
            result.copied += 1
            continue

        try:
            os.makedirs(os.path.dirname(item.dst_path), exist_ok=True)
            shutil.copy2(item.src_path, item.dst_path)
            result.copied += 1
        except (OSError, IOError) as e:
            result.errors.append({
                "action": "copy",
                "path": item.src_path,
                "target": item.dst_path,
                "error": str(e)
            })

    result.skipped = len(plan.skips)
    return result


def verify_mirror(
    src_index: FileIndex,
    dst_root: str,
    progress_callback=None
) -> Tuple[bool, List[Dict]]:
    """
    Verify that destination mirrors source correctly.

    Checks that every file in source exists at the correct path in destination
    with matching MD5.

    Returns:
        Tuple of (success: bool, mismatches: list of {path, reason})
    """
    mismatches = []
    total = len(src_index)
    current = 0

    for src_file in src_index.all_files():
        current += 1
        if progress_callback:
            progress_callback(current, total, src_file.relative_path)

        dst_path = os.path.join(dst_root, src_file.relative_path.replace("/", os.sep))

        if not os.path.exists(dst_path):
            mismatches.append({
                "path": src_file.relative_path,
                "reason": "File missing in destination"
            })
            continue

        try:
            dst_stat = os.stat(dst_path)
            # Quick check: size must match
            if dst_stat.st_size != src_file.size:
                mismatches.append({
                    "path": src_file.relative_path,
                    "reason": f"Size mismatch: source={src_file.size}, dest={dst_stat.st_size}"
                })
                continue

            # Full check: MD5 must match
            dst_md5 = compute_md5(dst_path)
            if dst_md5 != src_file.md5:
                mismatches.append({
                    "path": src_file.relative_path,
                    "reason": f"MD5 mismatch: source={src_file.md5}, dest={dst_md5}"
                })

        except (OSError, IOError) as e:
            mismatches.append({
                "path": src_file.relative_path,
                "reason": f"Error reading destination: {e}"
            })

    return len(mismatches) == 0, mismatches


def execute_deletes(
    plan: SyncPlan,
    dry_run: bool = False,
    progress_callback=None
) -> Tuple[int, List[Dict]]:
    """
    Execute delete operations from the sync plan.
    Should only be called after verification passes.

    Returns:
        Tuple of (deleted_count, errors)
    """
    deleted = 0
    errors = []

    total = len(plan.deletes)
    for i, item in enumerate(plan.deletes):
        if progress_callback:
            progress_callback(i + 1, total, item.dst_rel_path)

        if dry_run:
            deleted += 1
            continue

        try:
            os.remove(item.dst_path)
            deleted += 1
        except (OSError, IOError) as e:
            errors.append({
                "path": item.dst_path,
                "error": str(e)
            })

    return deleted, errors


def cleanup_empty_dirs(root: str, dry_run: bool = False) -> int:
    """
    Remove empty directories under root (bottom-up).

    Returns:
        Number of directories removed
    """
    removed = 0

    # Walk bottom-up
    for dirpath, dirnames, filenames in os.walk(root, topdown=False):
        # Skip root itself
        if dirpath == root:
            continue

        # Check if directory is empty (no files, no subdirs)
        if not dirnames and not filenames:
            if not dry_run:
                try:
                    os.rmdir(dirpath)
                    removed += 1
                except OSError:
                    pass
            else:
                removed += 1

    return removed


def print_sync_plan_summary(plan: SyncPlan):
    """Print a summary of the sync plan."""
    print(f"\nSync Plan Summary:")
    print(f"  Files to skip (up-to-date): {len(plan.skips)}")
    print(f"  Files to copy: {len(plan.copies)}")
    print(f"  Files to move: {len(plan.moves)}")
    print(f"  Files to delete: {len(plan.deletes)}")
    print()

    if plan.moves:
        print("Files to MOVE:")
        for item in plan.moves[:10]:  # Show first 10
            print(f"  {item.move_from} -> {item.dst_path}")
        if len(plan.moves) > 10:
            print(f"  ... and {len(plan.moves) - 10} more")
        print()

    if plan.copies:
        print("Files to COPY:")
        for item in plan.copies[:10]:
            print(f"  {item.src_rel_path} ({item.reason})")
        if len(plan.copies) > 10:
            print(f"  ... and {len(plan.copies) - 10} more")
        print()

    if plan.deletes:
        print("Files to DELETE (after verification):")
        for item in plan.deletes[:10]:
            print(f"  {item.dst_rel_path}")
        if len(plan.deletes) > 10:
            print(f"  ... and {len(plan.deletes) - 10} more")
        print()
