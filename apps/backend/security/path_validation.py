"""
Path traversal prevention utilities.

Provides functions to validate and sanitize file paths to prevent path traversal attacks.
"""

import os
import re
from pathlib import Path
from typing import Optional, Set


# Dangerous file extensions that should never be uploaded
DANGEROUS_EXTENSIONS = {
    ".exe", ".bat", ".cmd", ".com", ".pif", ".scr",  # Windows executables
    ".sh", ".bash", ".zsh",  # Shell scripts
    ".php", ".jsp", ".asp", ".aspx",  # Server-side scripts
    ".py", ".rb", ".pl", ".cgi",  # Other scripts
    ".jar", ".war",  # Java archives
    ".dll", ".so", ".dylib",  # Libraries
    ".app", ".deb", ".rpm",  # Packages
}

# Allowed file extensions for uploads
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".bmp"}
ALLOWED_DOCUMENT_EXTENSIONS = {".pdf", ".txt", ".doc", ".docx", ".xls", ".xlsx", ".csv"}
ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".webm", ".mov", ".avi"}

# Combine all allowed extensions
ALLOWED_EXTENSIONS = ALLOWED_IMAGE_EXTENSIONS | ALLOWED_DOCUMENT_EXTENSIONS | ALLOWED_VIDEO_EXTENSIONS

# Maximum file size (10MB)
MAX_FILE_SIZE = 10 * 1024 * 1024


def is_safe_filename(filename: str) -> bool:
    """
    Check if filename is safe (no path traversal, no dangerous characters).

    Args:
        filename: The filename to check

    Returns:
        True if filename is safe, False otherwise
    """
    if not filename:
        return False

    # Check for path traversal attempts
    if ".." in filename:
        return False

    # Check for absolute paths
    if filename.startswith("/") or filename.startswith("\\"):
        return False

    # Check for null bytes
    if "\x00" in filename:
        return False

    # Check for dangerous characters
    dangerous_chars = ["<", ">", ":", '"', "|", "?", "*"]
    if any(char in filename for char in dangerous_chars):
        return False

    # Check for hidden files (Unix)
    if filename.startswith("."):
        return False

    # Check for control characters
    if any(ord(char) < 32 for char in filename):
        return False

    return True


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename by removing or replacing dangerous characters.

    Args:
        filename: The filename to sanitize

    Returns:
        Sanitized filename
    """
    # Extract just the basename (remove any path components)
    filename = os.path.basename(filename)

    # Remove null bytes
    filename = filename.replace("\x00", "")

    # Remove path traversal attempts
    filename = filename.replace("..", "")

    # Replace spaces with underscores
    filename = filename.replace(" ", "_")

    # Remove dangerous characters
    filename = re.sub(r'[<>:"|?*]', "", filename)

    # Remove control characters
    filename = "".join(char for char in filename if ord(char) >= 32)

    # Remove leading dots (hidden files)
    filename = filename.lstrip(".")

    # Limit length (255 is typical filesystem limit)
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        filename = name[:255 - len(ext)] + ext

    return filename


def validate_file_extension(filename: str, allowed_extensions: Optional[Set[str]] = None) -> bool:
    """
    Validate that file extension is allowed.

    Args:
        filename: The filename to check
        allowed_extensions: Set of allowed extensions (defaults to ALLOWED_EXTENSIONS)

    Returns:
        True if extension is allowed, False otherwise
    """
    if allowed_extensions is None:
        allowed_extensions = ALLOWED_EXTENSIONS

    ext = os.path.splitext(filename)[1].lower()

    # Check if extension is dangerous
    if ext in DANGEROUS_EXTENSIONS:
        return False

    # Check if extension is in allowed list
    return ext in allowed_extensions


def validate_path_within_directory(file_path: Path, base_directory: Path) -> bool:
    """
    Validate that a path is within a base directory (prevent path traversal).

    Args:
        file_path: The path to validate
        base_directory: The base directory that should contain the path

    Returns:
        True if path is within directory, False otherwise
    """
    try:
        # Resolve to absolute paths
        file_path = file_path.resolve()
        base_directory = base_directory.resolve()

        # Check if file_path is relative to base_directory
        return file_path.is_relative_to(base_directory)
    except (ValueError, OSError):
        return False


def secure_join(base_path: Path, *paths: str) -> Optional[Path]:
    """
    Securely join paths, preventing path traversal.

    Args:
        base_path: Base directory path
        *paths: Path components to join

    Returns:
        Joined path if safe, None if path traversal detected
    """
    try:
        # Sanitize each path component
        safe_paths = [sanitize_filename(p) for p in paths]

        # Join paths
        result = base_path
        for p in safe_paths:
            result = result / p

        # Validate result is within base_path
        if not validate_path_within_directory(result, base_path):
            return None

        return result
    except (ValueError, OSError):
        return None


def validate_file_size(file_size: int, max_size: int = MAX_FILE_SIZE) -> bool:
    """
    Validate that file size is within acceptable limits.

    Args:
        file_size: Size of file in bytes
        max_size: Maximum allowed size in bytes

    Returns:
        True if size is acceptable, False otherwise
    """
    return 0 < file_size <= max_size


class FileUploadValidator:
    """
    Comprehensive file upload validator.

    Usage:
        validator = FileUploadValidator()
        if validator.validate(filename, file_size, file_content):
            # Safe to process file
            pass
    """

    def __init__(
        self,
        allowed_extensions: Optional[Set[str]] = None,
        max_size: int = MAX_FILE_SIZE
    ):
        """
        Initialize file upload validator.

        Args:
            allowed_extensions: Set of allowed file extensions
            max_size: Maximum file size in bytes
        """
        self.allowed_extensions = allowed_extensions or ALLOWED_EXTENSIONS
        self.max_size = max_size

    def validate(self, filename: str, file_size: int, file_content: Optional[bytes] = None) -> tuple[bool, Optional[str]]:
        """
        Validate file upload.

        Args:
            filename: Name of file being uploaded
            file_size: Size of file in bytes
            file_content: Optional file content for content validation

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Validate filename is safe
        if not is_safe_filename(filename):
            return False, "Filename contains invalid characters or path traversal attempt"

        # Validate file extension
        if not validate_file_extension(filename, self.allowed_extensions):
            return False, f"File extension not allowed. Allowed: {', '.join(sorted(self.allowed_extensions))}"

        # Validate file size
        if not validate_file_size(file_size, self.max_size):
            max_mb = self.max_size / (1024 * 1024)
            return False, f"File size exceeds maximum allowed size of {max_mb}MB"

        # Optional: Validate file content (magic bytes)
        if file_content is not None:
            if not self._validate_content_type(filename, file_content):
                return False, "File content does not match file extension"

        return True, None

    def _validate_content_type(self, filename: str, content: bytes) -> bool:
        """
        Validate file content matches extension (using magic bytes).

        Args:
            filename: Filename with extension
            content: File content (first few bytes)

        Returns:
            True if content matches extension
        """
        if len(content) < 8:
            return True  # Can't validate short files

        ext = os.path.splitext(filename)[1].lower()

        # Check magic bytes for common formats
        magic_bytes = {
            ".jpg": [b"\xFF\xD8\xFF"],
            ".jpeg": [b"\xFF\xD8\xFF"],
            ".png": [b"\x89PNG\r\n\x1a\n"],
            ".gif": [b"GIF87a", b"GIF89a"],
            ".pdf": [b"%PDF"],
            ".zip": [b"PK\x03\x04"],
        }

        if ext in magic_bytes:
            return any(content.startswith(magic) for magic in magic_bytes[ext])

        return True  # Don't validate unknown types
