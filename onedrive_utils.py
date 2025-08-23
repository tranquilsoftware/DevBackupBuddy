"""
OneDrive utility functions for handling online-only files.
On Windows, requires pywin32 (install with: pip install pywin32)
On non-Windows systems, OneDrive checks are skipped.
"""
import os
import sys
import time
from typing import Optional, Tuple

# Only import win32 modules on Windows
IS_WINDOWS = sys.platform == 'win32'
if IS_WINDOWS:
    try:
        import win32api
        import win32con
        import win32file
    except ImportError:
        IS_WINDOWS = False
        print("Warning: pywin32 not found. OneDrive integration will be disabled.")
else:
    print("Info: OneDrive integration is only available on Windows.")

class OneDriveUtils:
    @staticmethod
    def is_onedrive_file(path: str) -> bool:
        """
        Check if the file is stored in OneDrive.
        On non-Windows systems, always returns False.
        """
        if not IS_WINDOWS:
            return False
        return 'OneDrive' in os.path.abspath(path)
    
    @staticmethod
    def _get_file_attributes(path: str) -> int:
        """
        Get file attributes using Windows API.
        On non-Windows systems, returns 0 (no special attributes).
        """
        if not IS_WINDOWS:
            return 0
        try:
            return win32file.GetFileAttributesW(path)
        except Exception:
            return 0
    
    @staticmethod
    def _is_online_only(path: str) -> bool:
        """Check if a file is marked as 'online-only' in OneDrive."""
        if not os.path.exists(path):
            return False
            
        attrs = OneDriveUtils._get_file_attributes(path)
        # Check for FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS or FILE_ATTRIBUTE_RECALL_ON_OPEN
        return bool(attrs & (0x00400000 | 0x00040000))
    
    @staticmethod
    def _force_download_file(path: str) -> bool:
        """
        Force download of an online-only OneDrive file.
        On non-Windows systems, returns False.
        """
        if not IS_WINDOWS:
            return False
            
        try:
            # Try to open the file with exclusive access to force download
            handle = win32file.CreateFile(
                path,
                win32con.GENERIC_READ,
                win32con.FILE_SHARE_READ | win32con.FILE_SHARE_WRITE | win32con.FILE_SHARE_DELETE,
                None,
                win32con.OPEN_EXISTING,
                win32con.FILE_ATTRIBUTE_NORMAL,
                None
            )
            if handle:
                win32file.CloseHandle(handle)
                return True
            return False
        except Exception as e:
            print(f"Error forcing download of {path}: {e}")
            return False
    
    @staticmethod
    def ensure_file_downloaded(path: str, retries: int = 2, delay: float = 1.0) -> bool:
        """
        Ensure a OneDrive file is downloaded locally.
        
        Args:
            path: Path to the file
            retries: Number of retry attempts
            delay: Delay between retries in seconds
            
        Returns:
            bool: True if file is available locally, False otherwise
        """
        if not OneDriveUtils.is_onedrive_file(path):
            return True
            
        for attempt in range(retries + 1):
            try:
                if not OneDriveUtils._is_online_only(path):
                    return True
                    
                print(f"Downloading OneDrive file: {path}")
                if OneDriveUtils._force_download_file(path):
                    # Give OneDrive a moment to download the file
                    time.sleep(1)
                    if not OneDriveUtils._is_online_only(path):
                        return True
                
                if attempt < retries:
                    time.sleep(delay * (attempt + 1))  # Exponential backoff
                    
            except Exception as e:
                print(f"Error ensuring file is downloaded (attempt {attempt + 1}/{retries + 1}): {e}")
                if attempt == retries:
                    return False
                time.sleep(delay * (attempt + 1))
                
        return False