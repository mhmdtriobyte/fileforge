"""
FileForge Converters Module
===========================

Production-ready file conversion utilities for images, documents, and data files.

This module provides a clean, type-safe API for converting between various file formats
with support for progress callbacks, batch operations, and comprehensive error handling.

Supported Conversions:
- Images: PNG, JPG/JPEG, WEBP, BMP, GIF
- Documents: PDF to TXT, PDF to Images
- Data: CSV, JSON, Excel (XLSX)

Author: FileForge Team
License: MIT
"""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Protocol,
    Tuple,
    TypeVar,
    Union,
)

# Configure module logger
logger = logging.getLogger(__name__)


# =============================================================================
# Type Definitions and Protocols
# =============================================================================

# Progress callback signature: (current: int, total: int, message: str) -> None
ProgressCallback = Callable[[int, int, str], None]

# Generic type for conversion results
T = TypeVar("T")


class ConversionStatus(Enum):
    """Status codes for conversion operations."""

    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILURE = "failure"
    SKIPPED = "skipped"


@dataclass(frozen=True)
class ConversionStatistics:
    """Statistics about a conversion operation."""

    files_processed: int = 0
    files_succeeded: int = 0
    files_failed: int = 0
    files_skipped: int = 0
    total_bytes_read: int = 0
    total_bytes_written: int = 0
    duration_seconds: float = 0.0

    @property
    def success_rate(self) -> float:
        """Calculate the success rate as a percentage."""
        if self.files_processed == 0:
            return 0.0
        return (self.files_succeeded / self.files_processed) * 100


@dataclass
class ConversionResult:
    """Result of a file conversion operation."""

    status: ConversionStatus
    input_path: Path
    output_path: Optional[Path] = None
    error_message: Optional[str] = None
    statistics: ConversionStatistics = field(default_factory=ConversionStatistics)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_success(self) -> bool:
        """Check if the conversion was successful."""
        return self.status in (ConversionStatus.SUCCESS, ConversionStatus.PARTIAL_SUCCESS)

    def __repr__(self) -> str:
        status_str = self.status.value
        if self.is_success:
            return f"ConversionResult({status_str}, output={self.output_path})"
        return f"ConversionResult({status_str}, error={self.error_message})"


@dataclass
class BatchConversionResult:
    """Result of a batch conversion operation."""

    results: List[ConversionResult] = field(default_factory=list)
    statistics: ConversionStatistics = field(default_factory=ConversionStatistics)

    @property
    def status(self) -> ConversionStatus:
        """Determine overall status based on individual results."""
        if not self.results:
            return ConversionStatus.SKIPPED

        successes = sum(1 for r in self.results if r.is_success)
        if successes == len(self.results):
            return ConversionStatus.SUCCESS
        elif successes > 0:
            return ConversionStatus.PARTIAL_SUCCESS
        return ConversionStatus.FAILURE

    @property
    def is_success(self) -> bool:
        """Check if at least some conversions succeeded."""
        return self.status in (ConversionStatus.SUCCESS, ConversionStatus.PARTIAL_SUCCESS)

    def add_result(self, result: ConversionResult) -> None:
        """Add a conversion result to the batch."""
        self.results.append(result)
        self._update_statistics(result)

    def _update_statistics(self, result: ConversionResult) -> None:
        """Update batch statistics with a new result."""
        stats = result.statistics
        self.statistics = ConversionStatistics(
            files_processed=self.statistics.files_processed + 1,
            files_succeeded=self.statistics.files_succeeded + (1 if result.is_success else 0),
            files_failed=self.statistics.files_failed + (1 if result.status == ConversionStatus.FAILURE else 0),
            files_skipped=self.statistics.files_skipped + (1 if result.status == ConversionStatus.SKIPPED else 0),
            total_bytes_read=self.statistics.total_bytes_read + stats.total_bytes_read,
            total_bytes_written=self.statistics.total_bytes_written + stats.total_bytes_written,
            duration_seconds=self.statistics.duration_seconds + stats.duration_seconds,
        )


# =============================================================================
# Custom Exceptions
# =============================================================================

class ConversionError(Exception):
    """Base exception for conversion errors."""

    def __init__(self, message: str, input_path: Optional[Path] = None):
        super().__init__(message)
        self.message = message
        self.input_path = input_path


class UnsupportedFormatError(ConversionError):
    """Raised when a file format is not supported."""

    def __init__(self, format_name: str, supported_formats: List[str]):
        message = f"Unsupported format: '{format_name}'. Supported formats: {', '.join(supported_formats)}"
        super().__init__(message)
        self.format_name = format_name
        self.supported_formats = supported_formats


class FileNotFoundError(ConversionError):
    """Raised when input file is not found."""

    def __init__(self, path: Path):
        message = f"File not found: {path}"
        super().__init__(message, path)


class InvalidInputError(ConversionError):
    """Raised when input data is invalid or corrupted."""
    pass


class OutputError(ConversionError):
    """Raised when output cannot be written."""
    pass


# =============================================================================
# Utility Functions
# =============================================================================

def _ensure_output_dir(output_path: Path) -> None:
    """Ensure the output directory exists."""
    output_path.parent.mkdir(parents=True, exist_ok=True)


def _validate_input_file(input_path: Path) -> None:
    """Validate that input file exists and is readable."""
    if not input_path.exists():
        raise FileNotFoundError(input_path)
    if not input_path.is_file():
        raise InvalidInputError(f"Path is not a file: {input_path}", input_path)


def _get_file_size(path: Path) -> int:
    """Get file size in bytes, return 0 if file doesn't exist."""
    try:
        return path.stat().st_size
    except OSError:
        return 0


def _default_progress_callback(current: int, total: int, message: str) -> None:
    """Default no-op progress callback."""
    pass


# =============================================================================
# Image Converter
# =============================================================================

class ImageFormat(Enum):
    """Supported image formats."""

    PNG = "png"
    JPG = "jpg"
    JPEG = "jpeg"
    WEBP = "webp"
    BMP = "bmp"
    GIF = "gif"

    @classmethod
    def from_extension(cls, ext: str) -> "ImageFormat":
        """Get ImageFormat from file extension."""
        ext = ext.lower().lstrip(".")
        try:
            return cls(ext)
        except ValueError:
            raise UnsupportedFormatError(ext, [f.value for f in cls])

    @classmethod
    def supported_extensions(cls) -> List[str]:
        """Get list of supported file extensions."""
        return [f".{f.value}" for f in cls]

    def get_pillow_format(self) -> str:
        """Get the Pillow format string for this image format."""
        mapping = {
            ImageFormat.PNG: "PNG",
            ImageFormat.JPG: "JPEG",
            ImageFormat.JPEG: "JPEG",
            ImageFormat.WEBP: "WEBP",
            ImageFormat.BMP: "BMP",
            ImageFormat.GIF: "GIF",
        }
        return mapping[self]

    def supports_quality(self) -> bool:
        """Check if this format supports quality setting."""
        return self in (ImageFormat.JPG, ImageFormat.JPEG, ImageFormat.WEBP)

    def get_extension(self) -> str:
        """Get the file extension for this format."""
        # Normalize JPEG to JPG for file extension
        if self == ImageFormat.JPEG:
            return ".jpg"
        return f".{self.value}"


@dataclass
class ImageConversionOptions:
    """Options for image conversion."""

    quality: int = 85  # 1-100, only for lossy formats
    width: Optional[int] = None
    height: Optional[int] = None
    scale: Optional[float] = None  # Scale percentage (0.5 = 50%)
    preserve_aspect_ratio: bool = True
    optimize: bool = True

    def __post_init__(self) -> None:
        """Validate options after initialization."""
        if self.quality < 1 or self.quality > 100:
            raise ValueError("Quality must be between 1 and 100")
        if self.scale is not None and self.scale <= 0:
            raise ValueError("Scale must be positive")
        if self.width is not None and self.width <= 0:
            raise ValueError("Width must be positive")
        if self.height is not None and self.height <= 0:
            raise ValueError("Height must be positive")


class ImageConverter:
    """
    Converter for image files supporting multiple formats.

    Supports PNG, JPG/JPEG, WEBP, BMP, and GIF formats with options
    for quality control, resizing, and optimization.

    Example:
        >>> converter = ImageConverter()
        >>> result = converter.convert(
        ...     Path("input.png"),
        ...     Path("output.jpg"),
        ...     options=ImageConversionOptions(quality=90, scale=0.5)
        ... )
        >>> print(result.status)
        ConversionStatus.SUCCESS
    """

    SUPPORTED_FORMATS = ImageFormat

    def __init__(self) -> None:
        """Initialize the image converter."""
        self._pillow_available = self._check_pillow()

    def _check_pillow(self) -> bool:
        """Check if Pillow is available."""
        try:
            from PIL import Image
            return True
        except ImportError:
            return False

    def _ensure_pillow(self) -> None:
        """Ensure Pillow is available, raise if not."""
        if not self._pillow_available:
            raise ConversionError(
                "Pillow library is required for image conversion. "
                "Install it with: pip install Pillow"
            )

    def convert(
        self,
        input_path: Path,
        output_path: Path,
        output_format: Optional[ImageFormat] = None,
        options: Optional[ImageConversionOptions] = None,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> ConversionResult:
        """
        Convert a single image file to another format.

        Args:
            input_path: Path to the input image file.
            output_path: Path for the output image file.
            output_format: Target format (inferred from output_path if not specified).
            options: Conversion options (quality, resize, etc.).
            progress_callback: Callback for progress updates.

        Returns:
            ConversionResult with status, output path, and statistics.

        Raises:
            ConversionError: If conversion fails.
            UnsupportedFormatError: If format is not supported.
        """
        import time
        start_time = time.time()

        self._ensure_pillow()
        from PIL import Image

        progress = progress_callback or _default_progress_callback
        options = options or ImageConversionOptions()
        input_path = Path(input_path)
        output_path = Path(output_path)

        try:
            # Validate input
            _validate_input_file(input_path)
            progress(0, 100, f"Loading {input_path.name}...")

            # Determine output format
            if output_format is None:
                output_format = ImageFormat.from_extension(output_path.suffix)

            # Ensure output directory exists
            _ensure_output_dir(output_path)

            # Load image
            bytes_read = _get_file_size(input_path)
            with Image.open(input_path) as img:
                progress(20, 100, "Processing image...")

                # Store original size for metadata
                original_size = img.size

                # Convert to RGB if necessary for formats that don't support alpha
                if output_format in (ImageFormat.JPG, ImageFormat.JPEG, ImageFormat.BMP):
                    if img.mode in ("RGBA", "P", "LA"):
                        # Create white background for transparency
                        background = Image.new("RGB", img.size, (255, 255, 255))
                        if img.mode == "P":
                            img = img.convert("RGBA")
                        if img.mode in ("RGBA", "LA"):
                            background.paste(img, mask=img.split()[-1])
                        img = background
                    elif img.mode != "RGB":
                        img = img.convert("RGB")

                progress(40, 100, "Applying transformations...")

                # Apply resize if specified
                if options.scale is not None:
                    new_width = int(img.width * options.scale)
                    new_height = int(img.height * options.scale)
                    img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                elif options.width is not None or options.height is not None:
                    new_size = self._calculate_new_size(
                        img.size,
                        options.width,
                        options.height,
                        options.preserve_aspect_ratio,
                    )
                    img = img.resize(new_size, Image.Resampling.LANCZOS)

                progress(60, 100, "Saving image...")

                # Prepare save parameters
                save_kwargs: Dict[str, Any] = {}
                pillow_format = output_format.get_pillow_format()

                if output_format.supports_quality():
                    save_kwargs["quality"] = options.quality

                if options.optimize:
                    if output_format in (ImageFormat.PNG, ImageFormat.JPG, ImageFormat.JPEG):
                        save_kwargs["optimize"] = True

                # Handle GIF-specific options
                if output_format == ImageFormat.GIF:
                    if img.mode not in ("P", "L"):
                        img = img.convert("P", palette=Image.Palette.ADAPTIVE, colors=256)

                # Save the image
                img.save(output_path, format=pillow_format, **save_kwargs)

                progress(100, 100, "Conversion complete!")

                # Calculate statistics
                bytes_written = _get_file_size(output_path)
                duration = time.time() - start_time

                return ConversionResult(
                    status=ConversionStatus.SUCCESS,
                    input_path=input_path,
                    output_path=output_path,
                    statistics=ConversionStatistics(
                        files_processed=1,
                        files_succeeded=1,
                        total_bytes_read=bytes_read,
                        total_bytes_written=bytes_written,
                        duration_seconds=duration,
                    ),
                    metadata={
                        "original_size": original_size,
                        "new_size": img.size,
                        "input_format": input_path.suffix.lower(),
                        "output_format": output_format.value,
                    },
                )

        except UnsupportedFormatError:
            raise
        except Exception as e:
            logger.exception(f"Image conversion failed: {input_path}")
            return ConversionResult(
                status=ConversionStatus.FAILURE,
                input_path=input_path,
                error_message=str(e),
                statistics=ConversionStatistics(
                    files_processed=1,
                    files_failed=1,
                    duration_seconds=time.time() - start_time,
                ),
            )

    def _calculate_new_size(
        self,
        original_size: Tuple[int, int],
        target_width: Optional[int],
        target_height: Optional[int],
        preserve_aspect_ratio: bool,
    ) -> Tuple[int, int]:
        """Calculate new image dimensions based on targets and aspect ratio."""
        orig_width, orig_height = original_size

        if not preserve_aspect_ratio:
            return (
                target_width or orig_width,
                target_height or orig_height,
            )

        if target_width and target_height:
            # Fit within bounds while preserving aspect ratio
            width_ratio = target_width / orig_width
            height_ratio = target_height / orig_height
            ratio = min(width_ratio, height_ratio)
            return (int(orig_width * ratio), int(orig_height * ratio))
        elif target_width:
            ratio = target_width / orig_width
            return (target_width, int(orig_height * ratio))
        elif target_height:
            ratio = target_height / orig_height
            return (int(orig_width * ratio), target_height)

        return original_size

    def batch_convert(
        self,
        input_paths: List[Path],
        output_dir: Path,
        output_format: ImageFormat,
        options: Optional[ImageConversionOptions] = None,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> BatchConversionResult:
        """
        Convert multiple image files to a specified format.

        Args:
            input_paths: List of input image file paths.
            output_dir: Directory for output files.
            output_format: Target format for all conversions.
            options: Conversion options applied to all files.
            progress_callback: Callback for overall progress updates.

        Returns:
            BatchConversionResult with individual results and statistics.
        """
        progress = progress_callback or _default_progress_callback
        batch_result = BatchConversionResult()
        total_files = len(input_paths)

        if total_files == 0:
            progress(0, 0, "No files to convert")
            return batch_result

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        for idx, input_path in enumerate(input_paths):
            input_path = Path(input_path)
            progress(idx, total_files, f"Converting {input_path.name}...")

            # Generate output path
            output_filename = input_path.stem + output_format.get_extension()
            output_path = output_dir / output_filename

            # Convert individual file (no individual progress for batch)
            result = self.convert(
                input_path,
                output_path,
                output_format,
                options,
            )
            batch_result.add_result(result)

        progress(total_files, total_files, "Batch conversion complete!")
        return batch_result


# =============================================================================
# Document Converter (PDF)
# =============================================================================

@dataclass
class PDFConversionOptions:
    """Options for PDF conversion."""

    page_range: Optional[Tuple[int, int]] = None  # (start, end), 0-indexed
    image_dpi: int = 200  # DPI for PDF to image conversion
    image_format: ImageFormat = ImageFormat.PNG

    def __post_init__(self) -> None:
        """Validate options after initialization."""
        if self.image_dpi < 72 or self.image_dpi > 600:
            raise ValueError("DPI must be between 72 and 600")
        if self.page_range is not None:
            start, end = self.page_range
            if start < 0 or end < start:
                raise ValueError("Invalid page range")


class DocumentConverter:
    """
    Converter for PDF documents.

    Supports extracting text from PDFs and converting PDF pages to images.

    Example:
        >>> converter = DocumentConverter()
        >>> result = converter.pdf_to_text(
        ...     Path("document.pdf"),
        ...     Path("output.txt")
        ... )
        >>> print(result.metadata["page_count"])
        10
    """

    def __init__(self) -> None:
        """Initialize the document converter."""
        self._pypdf_available = self._check_pypdf()
        self._pdf2image_available = self._check_pdf2image()

    def _check_pypdf(self) -> bool:
        """Check if pypdf is available."""
        try:
            from pypdf import PdfReader
            return True
        except ImportError:
            return False

    def _check_pdf2image(self) -> bool:
        """Check if pdf2image and dependencies are available."""
        try:
            from pdf2image import convert_from_path
            return True
        except ImportError:
            return False

    def _ensure_pypdf(self) -> None:
        """Ensure pypdf is available."""
        if not self._pypdf_available:
            raise ConversionError(
                "pypdf library is required for PDF text extraction. "
                "Install it with: pip install pypdf"
            )

    def _ensure_pdf2image(self) -> None:
        """Ensure pdf2image is available."""
        if not self._pdf2image_available:
            raise ConversionError(
                "pdf2image library is required for PDF to image conversion. "
                "Install it with: pip install pdf2image. "
                "Also ensure poppler is installed on your system."
            )

    def pdf_to_text(
        self,
        input_path: Path,
        output_path: Path,
        options: Optional[PDFConversionOptions] = None,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> ConversionResult:
        """
        Extract text from a PDF file.

        Args:
            input_path: Path to the input PDF file.
            output_path: Path for the output text file.
            options: Conversion options (page range, etc.).
            progress_callback: Callback for progress updates.

        Returns:
            ConversionResult with extracted text statistics.
        """
        import time
        start_time = time.time()

        self._ensure_pypdf()
        from pypdf import PdfReader

        progress = progress_callback or _default_progress_callback
        options = options or PDFConversionOptions()
        input_path = Path(input_path)
        output_path = Path(output_path)

        try:
            _validate_input_file(input_path)
            progress(0, 100, f"Reading PDF: {input_path.name}...")

            bytes_read = _get_file_size(input_path)
            _ensure_output_dir(output_path)

            reader = PdfReader(input_path)
            total_pages = len(reader.pages)

            # Determine page range
            start_page = 0
            end_page = total_pages
            if options.page_range:
                start_page = min(options.page_range[0], total_pages - 1)
                end_page = min(options.page_range[1] + 1, total_pages)

            pages_to_process = end_page - start_page
            extracted_text: List[str] = []
            total_chars = 0

            for idx, page_num in enumerate(range(start_page, end_page)):
                progress_pct = int((idx / pages_to_process) * 80) + 10
                progress(progress_pct, 100, f"Extracting page {page_num + 1}/{total_pages}...")

                page = reader.pages[page_num]
                text = page.extract_text() or ""
                extracted_text.append(f"--- Page {page_num + 1} ---\n{text}\n")
                total_chars += len(text)

            progress(90, 100, "Writing output file...")

            # Write to output file
            full_text = "\n".join(extracted_text)
            output_path.write_text(full_text, encoding="utf-8")

            bytes_written = _get_file_size(output_path)
            duration = time.time() - start_time

            progress(100, 100, "Text extraction complete!")

            return ConversionResult(
                status=ConversionStatus.SUCCESS,
                input_path=input_path,
                output_path=output_path,
                statistics=ConversionStatistics(
                    files_processed=1,
                    files_succeeded=1,
                    total_bytes_read=bytes_read,
                    total_bytes_written=bytes_written,
                    duration_seconds=duration,
                ),
                metadata={
                    "page_count": total_pages,
                    "pages_extracted": pages_to_process,
                    "total_characters": total_chars,
                },
            )

        except Exception as e:
            logger.exception(f"PDF text extraction failed: {input_path}")
            return ConversionResult(
                status=ConversionStatus.FAILURE,
                input_path=input_path,
                error_message=str(e),
                statistics=ConversionStatistics(
                    files_processed=1,
                    files_failed=1,
                    duration_seconds=time.time() - start_time,
                ),
            )

    def pdf_to_images(
        self,
        input_path: Path,
        output_dir: Path,
        options: Optional[PDFConversionOptions] = None,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> ConversionResult:
        """
        Convert PDF pages to images.

        Args:
            input_path: Path to the input PDF file.
            output_dir: Directory for output image files.
            options: Conversion options (DPI, format, page range).
            progress_callback: Callback for progress updates.

        Returns:
            ConversionResult with list of generated image paths in metadata.
        """
        import time
        start_time = time.time()

        self._ensure_pdf2image()
        from pdf2image import convert_from_path
        from pdf2image.exceptions import PDFInfoNotInstalledError, PDFPageCountError

        progress = progress_callback or _default_progress_callback
        options = options or PDFConversionOptions()
        input_path = Path(input_path)
        output_dir = Path(output_dir)

        try:
            _validate_input_file(input_path)
            progress(0, 100, f"Loading PDF: {input_path.name}...")

            bytes_read = _get_file_size(input_path)
            output_dir.mkdir(parents=True, exist_ok=True)

            # Convert PDF pages to images
            convert_kwargs: Dict[str, Any] = {
                "dpi": options.image_dpi,
            }

            if options.page_range:
                # pdf2image uses 1-indexed pages
                convert_kwargs["first_page"] = options.page_range[0] + 1
                convert_kwargs["last_page"] = options.page_range[1] + 1

            progress(10, 100, "Converting pages to images...")

            try:
                images = convert_from_path(str(input_path), **convert_kwargs)
            except PDFInfoNotInstalledError:
                raise ConversionError(
                    "Poppler is not installed. Please install poppler:\n"
                    "  - Windows: Download from https://github.com/osber/poppler/releases\n"
                    "  - macOS: brew install poppler\n"
                    "  - Linux: apt-get install poppler-utils"
                )
            except PDFPageCountError:
                raise ConversionError(f"Could not get page count from PDF: {input_path}")

            total_images = len(images)
            output_paths: List[Path] = []
            total_bytes_written = 0

            # Determine the format and extension
            pillow_format = options.image_format.get_pillow_format()
            extension = options.image_format.get_extension()

            for idx, image in enumerate(images):
                progress_pct = int((idx / total_images) * 80) + 15
                page_num = (options.page_range[0] if options.page_range else 0) + idx + 1
                progress(progress_pct, 100, f"Saving page {page_num}...")

                output_filename = f"{input_path.stem}_page_{page_num:04d}{extension}"
                output_path = output_dir / output_filename

                save_kwargs: Dict[str, Any] = {}
                if options.image_format.supports_quality():
                    save_kwargs["quality"] = 90

                image.save(output_path, format=pillow_format, **save_kwargs)
                output_paths.append(output_path)
                total_bytes_written += _get_file_size(output_path)

            duration = time.time() - start_time
            progress(100, 100, "PDF to images conversion complete!")

            return ConversionResult(
                status=ConversionStatus.SUCCESS,
                input_path=input_path,
                output_path=output_dir,
                statistics=ConversionStatistics(
                    files_processed=1,
                    files_succeeded=1,
                    total_bytes_read=bytes_read,
                    total_bytes_written=total_bytes_written,
                    duration_seconds=duration,
                ),
                metadata={
                    "page_count": total_images,
                    "dpi": options.image_dpi,
                    "image_format": options.image_format.value,
                    "output_files": [str(p) for p in output_paths],
                },
            )

        except ConversionError:
            raise
        except Exception as e:
            logger.exception(f"PDF to images conversion failed: {input_path}")
            return ConversionResult(
                status=ConversionStatus.FAILURE,
                input_path=input_path,
                error_message=str(e),
                statistics=ConversionStatistics(
                    files_processed=1,
                    files_failed=1,
                    duration_seconds=time.time() - start_time,
                ),
            )


# =============================================================================
# Data Converter (CSV, JSON, Excel)
# =============================================================================

class DataFormat(Enum):
    """Supported data formats."""

    CSV = "csv"
    JSON = "json"
    EXCEL = "xlsx"

    @classmethod
    def from_extension(cls, ext: str) -> "DataFormat":
        """Get DataFormat from file extension."""
        ext = ext.lower().lstrip(".")
        mapping = {
            "csv": cls.CSV,
            "json": cls.JSON,
            "xlsx": cls.EXCEL,
            "xls": cls.EXCEL,
        }
        if ext not in mapping:
            raise UnsupportedFormatError(ext, list(mapping.keys()))
        return mapping[ext]

    @classmethod
    def supported_extensions(cls) -> List[str]:
        """Get list of supported file extensions."""
        return [".csv", ".json", ".xlsx", ".xls"]


@dataclass
class DataConversionOptions:
    """Options for data conversion."""

    # CSV options
    csv_delimiter: str = ","
    csv_encoding: str = "utf-8"
    csv_header: bool = True

    # JSON options
    json_indent: Optional[int] = 2  # None for compact, 2 or 4 for pretty
    json_orient: str = "records"  # records, columns, index, split, table

    # Excel options
    excel_sheet_name: str = "Sheet1"
    excel_index: bool = False

    # General options
    date_format: Optional[str] = None  # e.g., "%Y-%m-%d"

    def __post_init__(self) -> None:
        """Validate options after initialization."""
        valid_orients = ["records", "columns", "index", "split", "table", "values"]
        if self.json_orient not in valid_orients:
            raise ValueError(f"Invalid json_orient. Must be one of: {valid_orients}")


class DataConverter:
    """
    Converter for data files (CSV, JSON, Excel).

    Supports bidirectional conversion between CSV, JSON, and Excel formats
    with options for formatting, encoding, and structure.

    Example:
        >>> converter = DataConverter()
        >>> result = converter.convert(
        ...     Path("data.csv"),
        ...     Path("output.json"),
        ...     options=DataConversionOptions(json_indent=4)
        ... )
        >>> print(result.metadata["row_count"])
        1000
    """

    SUPPORTED_FORMATS = DataFormat

    def __init__(self) -> None:
        """Initialize the data converter."""
        self._pandas_available = self._check_pandas()
        self._openpyxl_available = self._check_openpyxl()

    def _check_pandas(self) -> bool:
        """Check if pandas is available."""
        try:
            import pandas
            return True
        except ImportError:
            return False

    def _check_openpyxl(self) -> bool:
        """Check if openpyxl is available."""
        try:
            import openpyxl
            return True
        except ImportError:
            return False

    def _ensure_pandas(self) -> None:
        """Ensure pandas is available."""
        if not self._pandas_available:
            raise ConversionError(
                "pandas library is required for data conversion. "
                "Install it with: pip install pandas"
            )

    def _ensure_openpyxl(self) -> None:
        """Ensure openpyxl is available."""
        if not self._openpyxl_available:
            raise ConversionError(
                "openpyxl library is required for Excel conversion. "
                "Install it with: pip install openpyxl"
            )

    def convert(
        self,
        input_path: Path,
        output_path: Path,
        output_format: Optional[DataFormat] = None,
        options: Optional[DataConversionOptions] = None,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> ConversionResult:
        """
        Convert a data file to another format.

        Args:
            input_path: Path to the input data file.
            output_path: Path for the output data file.
            output_format: Target format (inferred from output_path if not specified).
            options: Conversion options (formatting, encoding, etc.).
            progress_callback: Callback for progress updates.

        Returns:
            ConversionResult with conversion statistics.
        """
        input_path = Path(input_path)
        output_path = Path(output_path)

        # Determine formats
        input_format = DataFormat.from_extension(input_path.suffix)
        if output_format is None:
            output_format = DataFormat.from_extension(output_path.suffix)

        # Route to specific converter
        conversion_map = {
            (DataFormat.CSV, DataFormat.JSON): self.csv_to_json,
            (DataFormat.JSON, DataFormat.CSV): self.json_to_csv,
            (DataFormat.CSV, DataFormat.EXCEL): self.csv_to_excel,
            (DataFormat.EXCEL, DataFormat.CSV): self.excel_to_csv,
            (DataFormat.JSON, DataFormat.EXCEL): self.json_to_excel,
            (DataFormat.EXCEL, DataFormat.JSON): self.excel_to_json,
        }

        converter_func = conversion_map.get((input_format, output_format))
        if converter_func is None:
            if input_format == output_format:
                raise ConversionError(
                    f"Source and target formats are the same: {input_format.value}"
                )
            raise ConversionError(
                f"Conversion from {input_format.value} to {output_format.value} "
                "is not supported"
            )

        return converter_func(input_path, output_path, options, progress_callback)

    def csv_to_json(
        self,
        input_path: Path,
        output_path: Path,
        options: Optional[DataConversionOptions] = None,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> ConversionResult:
        """Convert CSV file to JSON format."""
        import time
        start_time = time.time()

        self._ensure_pandas()
        import pandas as pd

        progress = progress_callback or _default_progress_callback
        options = options or DataConversionOptions()
        input_path = Path(input_path)
        output_path = Path(output_path)

        try:
            _validate_input_file(input_path)
            progress(0, 100, f"Reading CSV: {input_path.name}...")

            bytes_read = _get_file_size(input_path)
            _ensure_output_dir(output_path)

            # Read CSV
            df = pd.read_csv(
                input_path,
                delimiter=options.csv_delimiter,
                encoding=options.csv_encoding,
                header=0 if options.csv_header else None,
            )

            progress(50, 100, "Converting to JSON...")

            # Convert to JSON
            json_str = df.to_json(
                orient=options.json_orient,
                indent=options.json_indent,
                date_format=options.date_format or "iso",
            )

            progress(80, 100, "Writing JSON file...")

            output_path.write_text(json_str, encoding="utf-8")

            bytes_written = _get_file_size(output_path)
            duration = time.time() - start_time

            progress(100, 100, "Conversion complete!")

            return ConversionResult(
                status=ConversionStatus.SUCCESS,
                input_path=input_path,
                output_path=output_path,
                statistics=ConversionStatistics(
                    files_processed=1,
                    files_succeeded=1,
                    total_bytes_read=bytes_read,
                    total_bytes_written=bytes_written,
                    duration_seconds=duration,
                ),
                metadata={
                    "row_count": len(df),
                    "column_count": len(df.columns),
                    "columns": list(df.columns),
                },
            )

        except Exception as e:
            logger.exception(f"CSV to JSON conversion failed: {input_path}")
            return ConversionResult(
                status=ConversionStatus.FAILURE,
                input_path=input_path,
                error_message=str(e),
                statistics=ConversionStatistics(
                    files_processed=1,
                    files_failed=1,
                    duration_seconds=time.time() - start_time,
                ),
            )

    def json_to_csv(
        self,
        input_path: Path,
        output_path: Path,
        options: Optional[DataConversionOptions] = None,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> ConversionResult:
        """Convert JSON file to CSV format."""
        import time
        start_time = time.time()

        self._ensure_pandas()
        import pandas as pd

        progress = progress_callback or _default_progress_callback
        options = options or DataConversionOptions()
        input_path = Path(input_path)
        output_path = Path(output_path)

        try:
            _validate_input_file(input_path)
            progress(0, 100, f"Reading JSON: {input_path.name}...")

            bytes_read = _get_file_size(input_path)
            _ensure_output_dir(output_path)

            # Read JSON
            json_content = input_path.read_text(encoding="utf-8")
            data = json.loads(json_content)

            progress(30, 100, "Parsing JSON structure...")

            # Handle different JSON structures
            if isinstance(data, list):
                df = pd.DataFrame(data)
            elif isinstance(data, dict):
                # Try to detect the orient used
                if "data" in data and "columns" in data:
                    # table orient
                    df = pd.DataFrame(data["data"], columns=data["columns"])
                elif "columns" in data and "index" in data:
                    # split orient
                    df = pd.read_json(json_content, orient="split")
                else:
                    # Try records-like dict or convert dict to single row
                    try:
                        df = pd.DataFrame([data])
                    except Exception:
                        df = pd.DataFrame(data)
            else:
                raise InvalidInputError(
                    f"Unsupported JSON structure in {input_path}",
                    input_path,
                )

            progress(60, 100, "Writing CSV file...")

            # Write CSV
            df.to_csv(
                output_path,
                sep=options.csv_delimiter,
                encoding=options.csv_encoding,
                index=False,
                header=options.csv_header,
            )

            bytes_written = _get_file_size(output_path)
            duration = time.time() - start_time

            progress(100, 100, "Conversion complete!")

            return ConversionResult(
                status=ConversionStatus.SUCCESS,
                input_path=input_path,
                output_path=output_path,
                statistics=ConversionStatistics(
                    files_processed=1,
                    files_succeeded=1,
                    total_bytes_read=bytes_read,
                    total_bytes_written=bytes_written,
                    duration_seconds=duration,
                ),
                metadata={
                    "row_count": len(df),
                    "column_count": len(df.columns),
                    "columns": list(df.columns),
                },
            )

        except Exception as e:
            logger.exception(f"JSON to CSV conversion failed: {input_path}")
            return ConversionResult(
                status=ConversionStatus.FAILURE,
                input_path=input_path,
                error_message=str(e),
                statistics=ConversionStatistics(
                    files_processed=1,
                    files_failed=1,
                    duration_seconds=time.time() - start_time,
                ),
            )

    def csv_to_excel(
        self,
        input_path: Path,
        output_path: Path,
        options: Optional[DataConversionOptions] = None,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> ConversionResult:
        """Convert CSV file to Excel format."""
        import time
        start_time = time.time()

        self._ensure_pandas()
        self._ensure_openpyxl()
        import pandas as pd

        progress = progress_callback or _default_progress_callback
        options = options or DataConversionOptions()
        input_path = Path(input_path)
        output_path = Path(output_path)

        try:
            _validate_input_file(input_path)
            progress(0, 100, f"Reading CSV: {input_path.name}...")

            bytes_read = _get_file_size(input_path)
            _ensure_output_dir(output_path)

            # Read CSV
            df = pd.read_csv(
                input_path,
                delimiter=options.csv_delimiter,
                encoding=options.csv_encoding,
                header=0 if options.csv_header else None,
            )

            progress(50, 100, "Writing Excel file...")

            # Write Excel
            df.to_excel(
                output_path,
                sheet_name=options.excel_sheet_name,
                index=options.excel_index,
                engine="openpyxl",
            )

            bytes_written = _get_file_size(output_path)
            duration = time.time() - start_time

            progress(100, 100, "Conversion complete!")

            return ConversionResult(
                status=ConversionStatus.SUCCESS,
                input_path=input_path,
                output_path=output_path,
                statistics=ConversionStatistics(
                    files_processed=1,
                    files_succeeded=1,
                    total_bytes_read=bytes_read,
                    total_bytes_written=bytes_written,
                    duration_seconds=duration,
                ),
                metadata={
                    "row_count": len(df),
                    "column_count": len(df.columns),
                    "columns": list(df.columns),
                    "sheet_name": options.excel_sheet_name,
                },
            )

        except Exception as e:
            logger.exception(f"CSV to Excel conversion failed: {input_path}")
            return ConversionResult(
                status=ConversionStatus.FAILURE,
                input_path=input_path,
                error_message=str(e),
                statistics=ConversionStatistics(
                    files_processed=1,
                    files_failed=1,
                    duration_seconds=time.time() - start_time,
                ),
            )

    def excel_to_csv(
        self,
        input_path: Path,
        output_path: Path,
        options: Optional[DataConversionOptions] = None,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> ConversionResult:
        """Convert Excel file to CSV format."""
        import time
        start_time = time.time()

        self._ensure_pandas()
        self._ensure_openpyxl()
        import pandas as pd

        progress = progress_callback or _default_progress_callback
        options = options or DataConversionOptions()
        input_path = Path(input_path)
        output_path = Path(output_path)

        try:
            _validate_input_file(input_path)
            progress(0, 100, f"Reading Excel: {input_path.name}...")

            bytes_read = _get_file_size(input_path)
            _ensure_output_dir(output_path)

            # Read Excel
            df = pd.read_excel(
                input_path,
                sheet_name=options.excel_sheet_name if options.excel_sheet_name != "Sheet1" else 0,
                engine="openpyxl",
            )

            progress(50, 100, "Writing CSV file...")

            # Write CSV
            df.to_csv(
                output_path,
                sep=options.csv_delimiter,
                encoding=options.csv_encoding,
                index=False,
                header=options.csv_header,
            )

            bytes_written = _get_file_size(output_path)
            duration = time.time() - start_time

            progress(100, 100, "Conversion complete!")

            return ConversionResult(
                status=ConversionStatus.SUCCESS,
                input_path=input_path,
                output_path=output_path,
                statistics=ConversionStatistics(
                    files_processed=1,
                    files_succeeded=1,
                    total_bytes_read=bytes_read,
                    total_bytes_written=bytes_written,
                    duration_seconds=duration,
                ),
                metadata={
                    "row_count": len(df),
                    "column_count": len(df.columns),
                    "columns": list(df.columns),
                },
            )

        except Exception as e:
            logger.exception(f"Excel to CSV conversion failed: {input_path}")
            return ConversionResult(
                status=ConversionStatus.FAILURE,
                input_path=input_path,
                error_message=str(e),
                statistics=ConversionStatistics(
                    files_processed=1,
                    files_failed=1,
                    duration_seconds=time.time() - start_time,
                ),
            )

    def json_to_excel(
        self,
        input_path: Path,
        output_path: Path,
        options: Optional[DataConversionOptions] = None,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> ConversionResult:
        """Convert JSON file to Excel format."""
        import time
        start_time = time.time()

        self._ensure_pandas()
        self._ensure_openpyxl()
        import pandas as pd

        progress = progress_callback or _default_progress_callback
        options = options or DataConversionOptions()
        input_path = Path(input_path)
        output_path = Path(output_path)

        try:
            _validate_input_file(input_path)
            progress(0, 100, f"Reading JSON: {input_path.name}...")

            bytes_read = _get_file_size(input_path)
            _ensure_output_dir(output_path)

            # Read JSON
            json_content = input_path.read_text(encoding="utf-8")
            data = json.loads(json_content)

            progress(30, 100, "Parsing JSON structure...")

            # Handle different JSON structures
            if isinstance(data, list):
                df = pd.DataFrame(data)
            elif isinstance(data, dict):
                if "data" in data and "columns" in data:
                    df = pd.DataFrame(data["data"], columns=data["columns"])
                elif "columns" in data and "index" in data:
                    df = pd.read_json(json_content, orient="split")
                else:
                    try:
                        df = pd.DataFrame([data])
                    except Exception:
                        df = pd.DataFrame(data)
            else:
                raise InvalidInputError(
                    f"Unsupported JSON structure in {input_path}",
                    input_path,
                )

            progress(60, 100, "Writing Excel file...")

            # Write Excel
            df.to_excel(
                output_path,
                sheet_name=options.excel_sheet_name,
                index=options.excel_index,
                engine="openpyxl",
            )

            bytes_written = _get_file_size(output_path)
            duration = time.time() - start_time

            progress(100, 100, "Conversion complete!")

            return ConversionResult(
                status=ConversionStatus.SUCCESS,
                input_path=input_path,
                output_path=output_path,
                statistics=ConversionStatistics(
                    files_processed=1,
                    files_succeeded=1,
                    total_bytes_read=bytes_read,
                    total_bytes_written=bytes_written,
                    duration_seconds=duration,
                ),
                metadata={
                    "row_count": len(df),
                    "column_count": len(df.columns),
                    "columns": list(df.columns),
                    "sheet_name": options.excel_sheet_name,
                },
            )

        except Exception as e:
            logger.exception(f"JSON to Excel conversion failed: {input_path}")
            return ConversionResult(
                status=ConversionStatus.FAILURE,
                input_path=input_path,
                error_message=str(e),
                statistics=ConversionStatistics(
                    files_processed=1,
                    files_failed=1,
                    duration_seconds=time.time() - start_time,
                ),
            )

    def excel_to_json(
        self,
        input_path: Path,
        output_path: Path,
        options: Optional[DataConversionOptions] = None,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> ConversionResult:
        """Convert Excel file to JSON format."""
        import time
        start_time = time.time()

        self._ensure_pandas()
        self._ensure_openpyxl()
        import pandas as pd

        progress = progress_callback or _default_progress_callback
        options = options or DataConversionOptions()
        input_path = Path(input_path)
        output_path = Path(output_path)

        try:
            _validate_input_file(input_path)
            progress(0, 100, f"Reading Excel: {input_path.name}...")

            bytes_read = _get_file_size(input_path)
            _ensure_output_dir(output_path)

            # Read Excel
            df = pd.read_excel(
                input_path,
                sheet_name=options.excel_sheet_name if options.excel_sheet_name != "Sheet1" else 0,
                engine="openpyxl",
            )

            progress(50, 100, "Converting to JSON...")

            # Convert to JSON
            json_str = df.to_json(
                orient=options.json_orient,
                indent=options.json_indent,
                date_format=options.date_format or "iso",
            )

            progress(80, 100, "Writing JSON file...")

            output_path.write_text(json_str, encoding="utf-8")

            bytes_written = _get_file_size(output_path)
            duration = time.time() - start_time

            progress(100, 100, "Conversion complete!")

            return ConversionResult(
                status=ConversionStatus.SUCCESS,
                input_path=input_path,
                output_path=output_path,
                statistics=ConversionStatistics(
                    files_processed=1,
                    files_succeeded=1,
                    total_bytes_read=bytes_read,
                    total_bytes_written=bytes_written,
                    duration_seconds=duration,
                ),
                metadata={
                    "row_count": len(df),
                    "column_count": len(df.columns),
                    "columns": list(df.columns),
                },
            )

        except Exception as e:
            logger.exception(f"Excel to JSON conversion failed: {input_path}")
            return ConversionResult(
                status=ConversionStatus.FAILURE,
                input_path=input_path,
                error_message=str(e),
                statistics=ConversionStatistics(
                    files_processed=1,
                    files_failed=1,
                    duration_seconds=time.time() - start_time,
                ),
            )

    def batch_convert(
        self,
        input_paths: List[Path],
        output_dir: Path,
        output_format: DataFormat,
        options: Optional[DataConversionOptions] = None,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> BatchConversionResult:
        """
        Convert multiple data files to a specified format.

        Args:
            input_paths: List of input data file paths.
            output_dir: Directory for output files.
            output_format: Target format for all conversions.
            options: Conversion options applied to all files.
            progress_callback: Callback for overall progress updates.

        Returns:
            BatchConversionResult with individual results and statistics.
        """
        progress = progress_callback or _default_progress_callback
        batch_result = BatchConversionResult()
        total_files = len(input_paths)

        if total_files == 0:
            progress(0, 0, "No files to convert")
            return batch_result

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Determine output extension
        ext_map = {
            DataFormat.CSV: ".csv",
            DataFormat.JSON: ".json",
            DataFormat.EXCEL: ".xlsx",
        }
        output_ext = ext_map[output_format]

        for idx, input_path in enumerate(input_paths):
            input_path = Path(input_path)
            progress(idx, total_files, f"Converting {input_path.name}...")

            # Generate output path
            output_filename = input_path.stem + output_ext
            output_path = output_dir / output_filename

            # Convert individual file
            result = self.convert(
                input_path,
                output_path,
                output_format,
                options,
            )
            batch_result.add_result(result)

        progress(total_files, total_files, "Batch conversion complete!")
        return batch_result


# =============================================================================
# Unified Converter Factory
# =============================================================================

class ConverterFactory:
    """
    Factory for creating and managing file converters.

    Provides a unified interface for all conversion operations and
    handles converter instantiation and caching.

    Example:
        >>> factory = ConverterFactory()
        >>> result = factory.convert(
        ...     Path("input.png"),
        ...     Path("output.jpg"),
        ...     progress_callback=lambda c, t, m: print(f"{c}/{t}: {m}")
        ... )
    """

    def __init__(self) -> None:
        """Initialize the converter factory."""
        self._image_converter: Optional[ImageConverter] = None
        self._document_converter: Optional[DocumentConverter] = None
        self._data_converter: Optional[DataConverter] = None

    @property
    def image_converter(self) -> ImageConverter:
        """Get or create the image converter instance."""
        if self._image_converter is None:
            self._image_converter = ImageConverter()
        return self._image_converter

    @property
    def document_converter(self) -> DocumentConverter:
        """Get or create the document converter instance."""
        if self._document_converter is None:
            self._document_converter = DocumentConverter()
        return self._document_converter

    @property
    def data_converter(self) -> DataConverter:
        """Get or create the data converter instance."""
        if self._data_converter is None:
            self._data_converter = DataConverter()
        return self._data_converter

    def get_supported_formats(self) -> Dict[str, List[str]]:
        """Get all supported file formats by category."""
        return {
            "image": ImageFormat.supported_extensions(),
            "document": [".pdf"],
            "data": DataFormat.supported_extensions(),
        }

    def get_format_category(self, path: Path) -> Optional[str]:
        """Determine the format category of a file."""
        ext = path.suffix.lower()

        if ext in [f.get_extension() for f in ImageFormat] or ext in [".jpg", ".jpeg"]:
            return "image"
        elif ext == ".pdf":
            return "document"
        elif ext in [".csv", ".json", ".xlsx", ".xls"]:
            return "data"

        return None

    def convert(
        self,
        input_path: Path,
        output_path: Path,
        options: Optional[Union[ImageConversionOptions, PDFConversionOptions, DataConversionOptions]] = None,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> ConversionResult:
        """
        Convert a file using the appropriate converter.

        Automatically detects the input format and routes to the correct converter.

        Args:
            input_path: Path to the input file.
            output_path: Path for the output file.
            options: Format-specific conversion options.
            progress_callback: Callback for progress updates.

        Returns:
            ConversionResult from the appropriate converter.

        Raises:
            UnsupportedFormatError: If the input format is not supported.
        """
        input_path = Path(input_path)
        output_path = Path(output_path)

        category = self.get_format_category(input_path)

        if category == "image":
            return self.image_converter.convert(
                input_path,
                output_path,
                options=options if isinstance(options, ImageConversionOptions) else None,
                progress_callback=progress_callback,
            )
        elif category == "document":
            # Determine document conversion type based on output
            output_ext = output_path.suffix.lower()
            if output_ext == ".txt":
                return self.document_converter.pdf_to_text(
                    input_path,
                    output_path,
                    options=options if isinstance(options, PDFConversionOptions) else None,
                    progress_callback=progress_callback,
                )
            elif output_ext in [".png", ".jpg", ".jpeg", ".webp"]:
                # For images, output_path is treated as directory
                return self.document_converter.pdf_to_images(
                    input_path,
                    output_path.parent / output_path.stem,
                    options=options if isinstance(options, PDFConversionOptions) else None,
                    progress_callback=progress_callback,
                )
            else:
                raise UnsupportedFormatError(
                    output_ext,
                    [".txt", ".png", ".jpg"],
                )
        elif category == "data":
            return self.data_converter.convert(
                input_path,
                output_path,
                options=options if isinstance(options, DataConversionOptions) else None,
                progress_callback=progress_callback,
            )
        else:
            all_formats = []
            for formats in self.get_supported_formats().values():
                all_formats.extend(formats)
            raise UnsupportedFormatError(input_path.suffix, all_formats)


# =============================================================================
# Module-Level Convenience Functions
# =============================================================================

# Global factory instance for convenience functions
_factory: Optional[ConverterFactory] = None


def _get_factory() -> ConverterFactory:
    """Get or create the global converter factory."""
    global _factory
    if _factory is None:
        _factory = ConverterFactory()
    return _factory


def convert_image(
    input_path: Union[str, Path],
    output_path: Union[str, Path],
    quality: int = 85,
    width: Optional[int] = None,
    height: Optional[int] = None,
    scale: Optional[float] = None,
    progress_callback: Optional[ProgressCallback] = None,
) -> ConversionResult:
    """
    Convert an image file to another format.

    Convenience function for single image conversion.

    Args:
        input_path: Path to input image.
        output_path: Path for output image.
        quality: Quality for lossy formats (1-100).
        width: Target width in pixels.
        height: Target height in pixels.
        scale: Scale factor (0.5 = 50%).
        progress_callback: Progress callback function.

    Returns:
        ConversionResult with conversion details.

    Example:
        >>> result = convert_image("photo.png", "photo.jpg", quality=90)
        >>> print(result.output_path)
        photo.jpg
    """
    options = ImageConversionOptions(
        quality=quality,
        width=width,
        height=height,
        scale=scale,
    )
    return _get_factory().image_converter.convert(
        Path(input_path),
        Path(output_path),
        options=options,
        progress_callback=progress_callback,
    )


def convert_pdf_to_text(
    input_path: Union[str, Path],
    output_path: Union[str, Path],
    page_range: Optional[Tuple[int, int]] = None,
    progress_callback: Optional[ProgressCallback] = None,
) -> ConversionResult:
    """
    Extract text from a PDF file.

    Convenience function for PDF text extraction.

    Args:
        input_path: Path to input PDF.
        output_path: Path for output text file.
        page_range: Optional (start, end) page range (0-indexed).
        progress_callback: Progress callback function.

    Returns:
        ConversionResult with extraction details.

    Example:
        >>> result = convert_pdf_to_text("document.pdf", "document.txt")
        >>> print(result.metadata["page_count"])
        10
    """
    options = PDFConversionOptions(page_range=page_range)
    return _get_factory().document_converter.pdf_to_text(
        Path(input_path),
        Path(output_path),
        options=options,
        progress_callback=progress_callback,
    )


def convert_pdf_to_images(
    input_path: Union[str, Path],
    output_dir: Union[str, Path],
    dpi: int = 200,
    image_format: str = "png",
    page_range: Optional[Tuple[int, int]] = None,
    progress_callback: Optional[ProgressCallback] = None,
) -> ConversionResult:
    """
    Convert PDF pages to images.

    Convenience function for PDF to image conversion.

    Args:
        input_path: Path to input PDF.
        output_dir: Directory for output images.
        dpi: Resolution for output images.
        image_format: Output image format (png, jpg, webp).
        page_range: Optional (start, end) page range (0-indexed).
        progress_callback: Progress callback function.

    Returns:
        ConversionResult with list of output files in metadata.

    Example:
        >>> result = convert_pdf_to_images("document.pdf", "pages/", dpi=300)
        >>> print(len(result.metadata["output_files"]))
        10
    """
    options = PDFConversionOptions(
        page_range=page_range,
        image_dpi=dpi,
        image_format=ImageFormat.from_extension(image_format),
    )
    return _get_factory().document_converter.pdf_to_images(
        Path(input_path),
        Path(output_dir),
        options=options,
        progress_callback=progress_callback,
    )


def convert_data(
    input_path: Union[str, Path],
    output_path: Union[str, Path],
    csv_delimiter: str = ",",
    json_indent: Optional[int] = 2,
    excel_sheet_name: str = "Sheet1",
    progress_callback: Optional[ProgressCallback] = None,
) -> ConversionResult:
    """
    Convert a data file (CSV, JSON, Excel) to another format.

    Convenience function for data format conversion.

    Args:
        input_path: Path to input data file.
        output_path: Path for output data file.
        csv_delimiter: Delimiter for CSV files.
        json_indent: Indentation for JSON output (None for compact).
        excel_sheet_name: Sheet name for Excel files.
        progress_callback: Progress callback function.

    Returns:
        ConversionResult with conversion details.

    Example:
        >>> result = convert_data("data.csv", "data.json", json_indent=4)
        >>> print(result.metadata["row_count"])
        1000
    """
    options = DataConversionOptions(
        csv_delimiter=csv_delimiter,
        json_indent=json_indent,
        excel_sheet_name=excel_sheet_name,
    )
    return _get_factory().data_converter.convert(
        Path(input_path),
        Path(output_path),
        options=options,
        progress_callback=progress_callback,
    )


def batch_convert_images(
    input_paths: List[Union[str, Path]],
    output_dir: Union[str, Path],
    output_format: str,
    quality: int = 85,
    scale: Optional[float] = None,
    progress_callback: Optional[ProgressCallback] = None,
) -> BatchConversionResult:
    """
    Convert multiple images to a specified format.

    Args:
        input_paths: List of input image paths.
        output_dir: Directory for output images.
        output_format: Target format (png, jpg, webp, etc.).
        quality: Quality for lossy formats.
        scale: Optional scale factor.
        progress_callback: Progress callback function.

    Returns:
        BatchConversionResult with all conversion results.

    Example:
        >>> results = batch_convert_images(
        ...     ["a.png", "b.png"],
        ...     "output/",
        ...     "jpg",
        ...     quality=90
        ... )
        >>> print(results.statistics.success_rate)
        100.0
    """
    options = ImageConversionOptions(quality=quality, scale=scale)
    return _get_factory().image_converter.batch_convert(
        [Path(p) for p in input_paths],
        Path(output_dir),
        ImageFormat.from_extension(output_format),
        options=options,
        progress_callback=progress_callback,
    )


def batch_convert_data(
    input_paths: List[Union[str, Path]],
    output_dir: Union[str, Path],
    output_format: str,
    progress_callback: Optional[ProgressCallback] = None,
) -> BatchConversionResult:
    """
    Convert multiple data files to a specified format.

    Args:
        input_paths: List of input data file paths.
        output_dir: Directory for output files.
        output_format: Target format (csv, json, xlsx).
        progress_callback: Progress callback function.

    Returns:
        BatchConversionResult with all conversion results.

    Example:
        >>> results = batch_convert_data(
        ...     ["a.csv", "b.csv"],
        ...     "output/",
        ...     "json"
        ... )
        >>> print(results.statistics.files_succeeded)
        2
    """
    return _get_factory().data_converter.batch_convert(
        [Path(p) for p in input_paths],
        Path(output_dir),
        DataFormat.from_extension(output_format),
        progress_callback=progress_callback,
    )


def get_supported_formats() -> Dict[str, Dict[str, Any]]:
    """
    Get all supported file formats by category.

    Returns:
        Dictionary with 'image', 'document', and 'data' keys,
        each containing 'input', 'output', and 'description' keys.

    Example:
        >>> formats = get_supported_formats()
        >>> print(formats['image']['input'])
        ['png', 'jpg', 'jpeg', 'webp', 'bmp', 'gif']
    """
    image_exts = [ext.lstrip('.') for ext in ImageFormat.supported_extensions()]
    data_exts = [ext.lstrip('.') for ext in DataFormat.supported_extensions()]

    return {
        "image": {
            "input": image_exts,
            "output": image_exts,
            "description": "Image file formats with quality/resize options",
        },
        "document": {
            "input": ["pdf"],
            "output": ["txt", "png"],
            "description": "PDF to text or page images",
        },
        "data": {
            "input": data_exts,
            "output": data_exts,
            "description": "Data and spreadsheet formats",
        },
    }


# =============================================================================
# Public API Exports
# =============================================================================

__all__ = [
    # Status and Results
    "ConversionStatus",
    "ConversionStatistics",
    "ConversionResult",
    "BatchConversionResult",

    # Exceptions
    "ConversionError",
    "UnsupportedFormatError",
    "FileNotFoundError",
    "InvalidInputError",
    "OutputError",

    # Format Enums
    "ImageFormat",
    "DataFormat",

    # Options
    "ImageConversionOptions",
    "PDFConversionOptions",
    "DataConversionOptions",

    # Converters
    "ImageConverter",
    "DocumentConverter",
    "DataConverter",
    "ConverterFactory",

    # Convenience Functions
    "convert_image",
    "convert_pdf_to_text",
    "convert_pdf_to_images",
    "convert_data",
    "batch_convert_images",
    "batch_convert_data",
    "get_supported_formats",

    # Type Aliases
    "ProgressCallback",
]
