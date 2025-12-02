"""
FileForge Backend Utilities

This module provides utility functions for file handling, type detection,
format compatibility mapping, and file cleanup operations.
"""

import logging
import mimetypes
import os
import shutil
import time
import uuid
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class FileCategory(str, Enum):
    """Enumeration of supported file categories."""
    IMAGE = "image"
    DOCUMENT = "document"
    DATA = "data"
    UNKNOWN = "unknown"


# Mapping of file extensions to their categories
EXTENSION_TO_CATEGORY: Dict[str, FileCategory] = {
    # Image formats
    ".png": FileCategory.IMAGE,
    ".jpg": FileCategory.IMAGE,
    ".jpeg": FileCategory.IMAGE,
    ".webp": FileCategory.IMAGE,
    ".bmp": FileCategory.IMAGE,
    ".gif": FileCategory.IMAGE,
    # Document formats
    ".pdf": FileCategory.DOCUMENT,
    ".txt": FileCategory.DOCUMENT,
    # Data formats
    ".csv": FileCategory.DATA,
    ".json": FileCategory.DATA,
    ".xlsx": FileCategory.DATA,
    ".xls": FileCategory.DATA,
}

# Mapping of input formats to their compatible output formats
FORMAT_COMPATIBILITY: Dict[str, List[str]] = {
    # Image conversions
    "png": ["jpg", "jpeg", "webp", "bmp", "gif"],
    "jpg": ["png", "webp", "bmp", "gif"],
    "jpeg": ["png", "webp", "bmp", "gif"],
    "webp": ["png", "jpg", "jpeg", "bmp", "gif"],
    "bmp": ["png", "jpg", "jpeg", "webp", "gif"],
    "gif": ["png", "jpg", "jpeg", "webp", "bmp"],
    # Document conversions
    "pdf": ["txt", "png", "jpg"],
    # Data conversions
    "csv": ["json", "xlsx"],
    "json": ["csv", "xlsx"],
    "xlsx": ["csv", "json"],
    "xls": ["csv", "json"],
}

# MIME type mappings
MIME_TO_EXTENSION: Dict[str, str] = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
    "image/bmp": ".bmp",
    "image/gif": ".gif",
    "application/pdf": ".pdf",
    "text/plain": ".txt",
    "text/csv": ".csv",
    "application/json": ".json",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    "application/vnd.ms-excel": ".xls",
}

# Default file expiry time in seconds (1 hour)
DEFAULT_FILE_EXPIRY_SECONDS = 3600


def generate_file_id() -> str:
    """
    Generate a unique file identifier.

    Returns:
        A unique UUID string for file identification.
    """
    return str(uuid.uuid4())


def detect_file_type(file_path: Path) -> tuple[str, FileCategory]:
    """
    Detect the file type based on extension and MIME type.

    Args:
        file_path: Path to the file to analyze.

    Returns:
        A tuple of (extension without dot, FileCategory).
    """
    extension = file_path.suffix.lower()

    # Try to get MIME type for additional validation
    mime_type, _ = mimetypes.guess_type(str(file_path))

    if extension in EXTENSION_TO_CATEGORY:
        category = EXTENSION_TO_CATEGORY[extension]
        return extension.lstrip("."), category

    # Fallback to MIME type detection
    if mime_type and mime_type in MIME_TO_EXTENSION:
        ext = MIME_TO_EXTENSION[mime_type]
        category = EXTENSION_TO_CATEGORY.get(ext, FileCategory.UNKNOWN)
        return ext.lstrip("."), category

    logger.warning(f"Unknown file type for: {file_path}")
    return extension.lstrip(".") if extension else "unknown", FileCategory.UNKNOWN


def get_compatible_formats(input_format: str) -> List[str]:
    """
    Get list of output formats compatible with the input format.

    Args:
        input_format: The input file format (without dot).

    Returns:
        List of compatible output format strings.
    """
    normalized_format = input_format.lower().lstrip(".")
    return FORMAT_COMPATIBILITY.get(normalized_format, [])


def get_all_supported_formats() -> Dict[str, Dict]:
    """
    Get all supported format conversions organized by category.

    Returns:
        Dictionary with format information organized by category.
    """
    formats_by_category: Dict[str, Dict] = {
        "image": {
            "formats": ["png", "jpg", "jpeg", "webp", "bmp", "gif"],
            "description": "Image file formats",
        },
        "document": {
            "formats": ["pdf", "txt"],
            "description": "Document file formats",
        },
        "data": {
            "formats": ["csv", "json", "xlsx", "xls"],
            "description": "Data file formats",
        },
    }

    conversions = {}
    for input_format, output_formats in FORMAT_COMPATIBILITY.items():
        conversions[input_format] = {
            "outputs": output_formats,
            "category": EXTENSION_TO_CATEGORY.get(
                f".{input_format}", FileCategory.UNKNOWN
            ).value,
        }

    return {
        "categories": formats_by_category,
        "conversions": conversions,
    }


def get_file_extension_for_format(format_name: str) -> str:
    """
    Get the file extension for a given format name.

    Args:
        format_name: Format name (e.g., 'jpg', 'pdf').

    Returns:
        File extension with dot (e.g., '.jpg').
    """
    normalized = format_name.lower().lstrip(".")
    return f".{normalized}"


def validate_conversion(input_format: str, output_format: str) -> bool:
    """
    Validate if a conversion between formats is supported.

    Args:
        input_format: Source format.
        output_format: Target format.

    Returns:
        True if conversion is supported, False otherwise.
    """
    compatible = get_compatible_formats(input_format)
    return output_format.lower().lstrip(".") in compatible


def cleanup_old_files(
    directory: Path,
    max_age_seconds: int = DEFAULT_FILE_EXPIRY_SECONDS,
    dry_run: bool = False
) -> List[Path]:
    """
    Remove files older than the specified age from a directory.

    Args:
        directory: Directory to clean up.
        max_age_seconds: Maximum age of files in seconds.
        dry_run: If True, only report files without deleting.

    Returns:
        List of paths that were (or would be) deleted.
    """
    deleted_files: List[Path] = []
    current_time = time.time()

    if not directory.exists():
        logger.warning(f"Cleanup directory does not exist: {directory}")
        return deleted_files

    try:
        for item in directory.iterdir():
            if item.is_file():
                file_age = current_time - item.stat().st_mtime
                if file_age > max_age_seconds:
                    if not dry_run:
                        try:
                            item.unlink()
                            logger.info(f"Deleted expired file: {item}")
                        except OSError as e:
                            logger.error(f"Failed to delete file {item}: {e}")
                            continue
                    deleted_files.append(item)
            elif item.is_dir():
                # Recursively clean subdirectories
                dir_age = current_time - item.stat().st_mtime
                if dir_age > max_age_seconds:
                    if not dry_run:
                        try:
                            shutil.rmtree(item)
                            logger.info(f"Deleted expired directory: {item}")
                        except OSError as e:
                            logger.error(f"Failed to delete directory {item}: {e}")
                            continue
                    deleted_files.append(item)
    except PermissionError as e:
        logger.error(f"Permission denied during cleanup: {e}")
    except Exception as e:
        logger.error(f"Unexpected error during cleanup: {e}")

    return deleted_files


def get_safe_filename(original_filename: str) -> str:
    """
    Sanitize a filename to prevent path traversal and other security issues.

    Args:
        original_filename: The original filename from user input.

    Returns:
        A sanitized filename safe for filesystem operations.
    """
    # Remove path separators and null bytes
    filename = original_filename.replace("/", "_").replace("\\", "_")
    filename = filename.replace("\x00", "")

    # Remove leading/trailing whitespace and dots
    filename = filename.strip().strip(".")

    # Limit filename length
    max_length = 255
    if len(filename) > max_length:
        name, ext = os.path.splitext(filename)
        name = name[:max_length - len(ext)]
        filename = name + ext

    # Fallback for empty filename
    if not filename:
        filename = "unnamed_file"

    return filename


def ensure_directory_exists(directory: Path) -> None:
    """
    Ensure a directory exists, creating it if necessary.

    Args:
        directory: Path to the directory.

    Raises:
        OSError: If directory cannot be created.
    """
    directory.mkdir(parents=True, exist_ok=True)


def get_file_size_mb(file_path: Path) -> float:
    """
    Get the size of a file in megabytes.

    Args:
        file_path: Path to the file.

    Returns:
        File size in megabytes.
    """
    return file_path.stat().st_size / (1024 * 1024)


class ConversionProgress:
    """
    Track conversion progress for a file.

    Attributes:
        file_id: Unique identifier for the file.
        status: Current status of the conversion.
        progress: Progress percentage (0-100).
        message: Human-readable status message.
        error: Error message if conversion failed.
        created_at: Timestamp when tracking started.
        updated_at: Timestamp of last update.
    """

    def __init__(self, file_id: str):
        self.file_id = file_id
        self.status = "pending"
        self.progress = 0
        self.message = "Waiting to start"
        self.error: Optional[str] = None
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.output_file_id: Optional[str] = None

    def update(
        self,
        status: Optional[str] = None,
        progress: Optional[int] = None,
        message: Optional[str] = None,
        error: Optional[str] = None,
        output_file_id: Optional[str] = None
    ) -> None:
        """Update the progress tracking."""
        if status is not None:
            self.status = status
        if progress is not None:
            self.progress = min(100, max(0, progress))
        if message is not None:
            self.message = message
        if error is not None:
            self.error = error
        if output_file_id is not None:
            self.output_file_id = output_file_id
        self.updated_at = datetime.now()

    def to_dict(self) -> Dict:
        """Convert progress to dictionary for API response."""
        return {
            "file_id": self.file_id,
            "status": self.status,
            "progress": self.progress,
            "message": self.message,
            "error": self.error,
            "output_file_id": self.output_file_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
