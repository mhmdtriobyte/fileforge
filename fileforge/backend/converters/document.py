"""
FileForge Document Converter

This module provides document conversion functionality, primarily focused on
PDF text extraction and PDF to image conversion using pypdf and Pillow.
"""

import io
import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from PIL import Image
from pypdf import PdfReader

from utils import ConversionProgress

logger = logging.getLogger(__name__)

# Supported formats
SUPPORTED_INPUT_FORMATS = {"pdf"}
SUPPORTED_OUTPUT_FORMATS = {"txt", "png", "jpg"}

# PDF processing limits
MAX_PDF_PAGES = 500
MAX_TEXT_SIZE_MB = 50


class DocumentConversionError(Exception):
    """Exception raised when document conversion fails."""
    pass


class DocumentConverter:
    """
    Handles document file conversions including PDF text extraction
    and PDF to image conversion.
    """

    def __init__(self):
        """Initialize the DocumentConverter."""
        self._format_handlers: Dict[str, Callable] = {
            "txt": self._convert_pdf_to_text,
            "png": self._convert_pdf_to_images,
            "jpg": self._convert_pdf_to_images,
            "jpeg": self._convert_pdf_to_images,
        }

    @staticmethod
    def get_supported_input_formats() -> List[str]:
        """Get list of supported input formats."""
        return list(SUPPORTED_INPUT_FORMATS)

    @staticmethod
    def get_supported_output_formats() -> List[str]:
        """Get list of supported output formats."""
        return list(SUPPORTED_OUTPUT_FORMATS)

    def convert(
        self,
        input_path: Path,
        output_path: Path,
        output_format: str,
        options: Optional[Dict[str, Any]] = None,
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> Path:
        """
        Convert a document file to the specified format.

        Args:
            input_path: Path to the source document file.
            output_path: Path where the converted file will be saved.
            output_format: Target format (txt, png, jpg).
            options: Conversion options including:
                - page_range: Optional tuple (start, end) for page selection
                - dpi: DPI for image conversion (default 150)
                - quality: JPEG quality (1-100, default 85)
            progress_callback: Optional callback function(progress, message).

        Returns:
            Path to the converted file (or directory for multi-page images).

        Raises:
            DocumentConversionError: If conversion fails.
            ValueError: If format is not supported.
        """
        options = options or {}
        output_format = output_format.lower().lstrip(".")

        # Validate formats
        if output_format not in SUPPORTED_OUTPUT_FORMATS:
            raise ValueError(
                f"Unsupported output format: {output_format}. "
                f"Supported formats: {SUPPORTED_OUTPUT_FORMATS}"
            )

        if not input_path.exists():
            raise DocumentConversionError(f"Input file not found: {input_path}")

        # Verify input is PDF
        input_format = input_path.suffix.lower().lstrip(".")
        if input_format not in SUPPORTED_INPUT_FORMATS:
            raise DocumentConversionError(
                f"Unsupported input format: {input_format}. "
                f"Supported: {SUPPORTED_INPUT_FORMATS}"
            )

        try:
            # Get the format handler
            handler = self._format_handlers.get(output_format)
            if not handler:
                raise ValueError(f"No handler for format: {output_format}")

            return handler(input_path, output_path, output_format, options, progress_callback)

        except Exception as e:
            logger.error(f"Document conversion failed: {e}")
            if isinstance(e, DocumentConversionError):
                raise
            raise DocumentConversionError(f"Conversion failed: {e}")

    def _convert_pdf_to_text(
        self,
        input_path: Path,
        output_path: Path,
        output_format: str,
        options: Dict[str, Any],
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> Path:
        """
        Extract text content from a PDF file.

        Args:
            input_path: Path to the PDF file.
            output_path: Path for the output text file.
            output_format: Output format (txt).
            options: Conversion options.
            progress_callback: Progress callback function.

        Returns:
            Path to the generated text file.
        """
        if progress_callback:
            progress_callback(10, "Opening PDF document")

        try:
            reader = PdfReader(str(input_path))
            total_pages = len(reader.pages)

            if total_pages > MAX_PDF_PAGES:
                raise DocumentConversionError(
                    f"PDF has {total_pages} pages, exceeds maximum of {MAX_PDF_PAGES}"
                )

            if progress_callback:
                progress_callback(20, f"Extracting text from {total_pages} pages")

            # Get page range if specified
            page_range = options.get("page_range")
            if page_range:
                start_page, end_page = page_range
                start_page = max(0, start_page)
                end_page = min(total_pages, end_page)
            else:
                start_page = 0
                end_page = total_pages

            # Extract text from each page
            text_parts: List[str] = []
            pages_to_process = end_page - start_page

            for i, page_num in enumerate(range(start_page, end_page)):
                page = reader.pages[page_num]
                page_text = page.extract_text()

                if page_text:
                    text_parts.append(f"--- Page {page_num + 1} ---\n")
                    text_parts.append(page_text)
                    text_parts.append("\n\n")

                # Update progress
                if progress_callback and pages_to_process > 0:
                    progress = 20 + int((i + 1) / pages_to_process * 70)
                    progress_callback(progress, f"Processing page {page_num + 1}/{total_pages}")

            # Combine and write text
            full_text = "".join(text_parts)

            # Check text size
            text_size_mb = len(full_text.encode("utf-8")) / (1024 * 1024)
            if text_size_mb > MAX_TEXT_SIZE_MB:
                raise DocumentConversionError(
                    f"Extracted text size ({text_size_mb:.1f}MB) exceeds maximum ({MAX_TEXT_SIZE_MB}MB)"
                )

            if progress_callback:
                progress_callback(95, "Writing text file")

            # Ensure output path has correct extension
            if output_path.suffix.lower() != ".txt":
                output_path = output_path.with_suffix(".txt")

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(full_text)

            if progress_callback:
                progress_callback(100, "Text extraction complete")

            logger.info(f"Extracted text from {input_path} to {output_path}")
            return output_path

        except Exception as e:
            if isinstance(e, DocumentConversionError):
                raise
            logger.error(f"PDF text extraction failed: {e}")
            raise DocumentConversionError(f"Failed to extract text from PDF: {e}")

    def _convert_pdf_to_images(
        self,
        input_path: Path,
        output_path: Path,
        output_format: str,
        options: Dict[str, Any],
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> Path:
        """
        Convert PDF pages to images.

        Note: This uses pypdf's built-in image extraction capabilities.
        For full page rendering, pdf2image with poppler would be needed.

        Args:
            input_path: Path to the PDF file.
            output_path: Path for the output images.
            output_format: Output format (png, jpg).
            options: Conversion options including dpi and quality.
            progress_callback: Progress callback function.

        Returns:
            Path to the output directory containing images.
        """
        if progress_callback:
            progress_callback(10, "Opening PDF document")

        try:
            reader = PdfReader(str(input_path))
            total_pages = len(reader.pages)

            if total_pages > MAX_PDF_PAGES:
                raise DocumentConversionError(
                    f"PDF has {total_pages} pages, exceeds maximum of {MAX_PDF_PAGES}"
                )

            # Get options
            quality = options.get("quality", 85)
            page_range = options.get("page_range")

            if page_range:
                start_page, end_page = page_range
                start_page = max(0, start_page)
                end_page = min(total_pages, end_page)
            else:
                start_page = 0
                end_page = total_pages

            if progress_callback:
                progress_callback(20, f"Processing {end_page - start_page} pages")

            # Create output directory
            output_dir = output_path.parent / f"{output_path.stem}_pages"
            output_dir.mkdir(parents=True, exist_ok=True)

            generated_files: List[Path] = []
            pages_to_process = end_page - start_page
            images_extracted = 0

            for i, page_num in enumerate(range(start_page, end_page)):
                page = reader.pages[page_num]

                # Extract images from the page
                page_images = self._extract_page_images(page, page_num)

                for img_idx, image in enumerate(page_images):
                    # Determine output filename
                    if output_format in ("jpg", "jpeg"):
                        ext = ".jpg"
                        save_format = "JPEG"
                        save_options = {"quality": quality}
                    else:
                        ext = ".png"
                        save_format = "PNG"
                        save_options = {"optimize": True}

                    output_file = output_dir / f"page_{page_num + 1:04d}_img_{img_idx + 1:02d}{ext}"

                    # Convert and save
                    if image.mode == "RGBA" and save_format == "JPEG":
                        # Handle transparency
                        background = Image.new("RGB", image.size, (255, 255, 255))
                        background.paste(image, mask=image.split()[-1])
                        image = background
                    elif image.mode not in ("RGB", "L") and save_format == "JPEG":
                        image = image.convert("RGB")

                    image.save(output_file, format=save_format, **save_options)
                    generated_files.append(output_file)
                    images_extracted += 1

                # Update progress
                if progress_callback and pages_to_process > 0:
                    progress = 20 + int((i + 1) / pages_to_process * 75)
                    progress_callback(progress, f"Processing page {page_num + 1}/{total_pages}")

            if images_extracted == 0:
                # No embedded images found, create a placeholder message
                logger.warning(f"No images found in PDF: {input_path}")

                # Create a simple text-based notification image
                notification_img = Image.new("RGB", (400, 100), (255, 255, 255))
                notification_file = output_dir / f"no_images_found{'.jpg' if output_format in ('jpg', 'jpeg') else '.png'}"
                notification_img.save(notification_file)
                generated_files.append(notification_file)

            if progress_callback:
                progress_callback(100, f"Extracted {images_extracted} images from PDF")

            logger.info(f"Extracted {images_extracted} images from {input_path} to {output_dir}")

            # Return the directory path
            return output_dir

        except Exception as e:
            if isinstance(e, DocumentConversionError):
                raise
            logger.error(f"PDF to image conversion failed: {e}")
            raise DocumentConversionError(f"Failed to convert PDF to images: {e}")

    def _extract_page_images(self, page, page_num: int) -> List[Image.Image]:
        """
        Extract embedded images from a PDF page.

        Args:
            page: pypdf Page object.
            page_num: Page number for logging.

        Returns:
            List of PIL Image objects.
        """
        images: List[Image.Image] = []

        try:
            if "/XObject" not in page["/Resources"]:
                return images

            x_objects = page["/Resources"]["/XObject"].get_object()

            for obj_name in x_objects:
                x_object = x_objects[obj_name]

                if x_object["/Subtype"] == "/Image":
                    try:
                        # Get image dimensions
                        width = x_object["/Width"]
                        height = x_object["/Height"]

                        # Get color space
                        color_space = x_object.get("/ColorSpace", "/DeviceRGB")
                        if isinstance(color_space, list):
                            color_space = color_space[0]

                        # Determine mode
                        if color_space == "/DeviceRGB":
                            mode = "RGB"
                        elif color_space == "/DeviceGray":
                            mode = "L"
                        elif color_space == "/DeviceCMYK":
                            mode = "CMYK"
                        else:
                            mode = "RGB"

                        # Get filter type
                        filters = x_object.get("/Filter", [])
                        if isinstance(filters, str):
                            filters = [filters]
                        elif not isinstance(filters, list):
                            filters = [str(filters)]

                        # Get raw data
                        data = x_object.get_data()

                        # Handle different filter types
                        if "/DCTDecode" in filters or "/JPXDecode" in filters:
                            # JPEG or JPEG2000 encoded
                            image = Image.open(io.BytesIO(data))
                        elif "/FlateDecode" in filters or not filters:
                            # Raw or zlib compressed data
                            bits_per_component = x_object.get("/BitsPerComponent", 8)

                            if mode == "L":
                                expected_size = width * height
                            elif mode == "RGB":
                                expected_size = width * height * 3
                            elif mode == "CMYK":
                                expected_size = width * height * 4
                            else:
                                expected_size = width * height * 3

                            if len(data) >= expected_size:
                                image = Image.frombytes(mode, (width, height), data[:expected_size])
                                if mode == "CMYK":
                                    image = image.convert("RGB")
                            else:
                                logger.warning(
                                    f"Image data size mismatch on page {page_num + 1}: "
                                    f"expected {expected_size}, got {len(data)}"
                                )
                                continue
                        else:
                            logger.warning(f"Unsupported filter type: {filters}")
                            continue

                        images.append(image)

                    except Exception as e:
                        logger.warning(f"Failed to extract image on page {page_num + 1}: {e}")
                        continue

        except Exception as e:
            logger.warning(f"Error processing page {page_num + 1} resources: {e}")

        return images

    def get_pdf_info(self, path: Path) -> Dict[str, Any]:
        """
        Get information about a PDF file.

        Args:
            path: Path to the PDF file.

        Returns:
            Dictionary with PDF information.
        """
        try:
            reader = PdfReader(str(path))

            # Get metadata
            metadata = reader.metadata or {}

            # Count total images
            total_images = 0
            for page in reader.pages:
                if "/XObject" in page["/Resources"]:
                    x_objects = page["/Resources"]["/XObject"].get_object()
                    for obj_name in x_objects:
                        if x_objects[obj_name]["/Subtype"] == "/Image":
                            total_images += 1

            return {
                "num_pages": len(reader.pages),
                "title": metadata.get("/Title", ""),
                "author": metadata.get("/Author", ""),
                "subject": metadata.get("/Subject", ""),
                "creator": metadata.get("/Creator", ""),
                "total_images": total_images,
                "is_encrypted": reader.is_encrypted,
            }
        except Exception as e:
            logger.error(f"Failed to get PDF info: {e}")
            return {}
