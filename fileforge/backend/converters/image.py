"""
FileForge Image Converter

This module provides image conversion functionality supporting multiple formats
including PNG, JPG, WEBP, BMP, and GIF using the Pillow library.
"""

import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from PIL import Image

from utils import ConversionProgress

logger = logging.getLogger(__name__)

# Supported image formats
SUPPORTED_INPUT_FORMATS = {"png", "jpg", "jpeg", "webp", "bmp", "gif"}
SUPPORTED_OUTPUT_FORMATS = {"png", "jpg", "jpeg", "webp", "bmp", "gif"}

# Formats that do not support transparency
NON_TRANSPARENT_FORMATS = {"jpg", "jpeg", "bmp"}

# Default quality settings
DEFAULT_QUALITY = 85
MIN_QUALITY = 1
MAX_QUALITY = 100

# Maximum image dimensions (to prevent memory issues)
MAX_DIMENSION = 10000


class ImageConversionError(Exception):
    """Exception raised when image conversion fails."""
    pass


class ImageConverter:
    """
    Handles image file conversions between supported formats.

    Supports PNG, JPG, WEBP, BMP, and GIF formats with configurable
    quality settings and proper transparency handling.
    """

    def __init__(self):
        """Initialize the ImageConverter."""
        self._format_handlers: Dict[str, Callable] = {
            "png": self._save_as_png,
            "jpg": self._save_as_jpeg,
            "jpeg": self._save_as_jpeg,
            "webp": self._save_as_webp,
            "bmp": self._save_as_bmp,
            "gif": self._save_as_gif,
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
        Convert an image file to the specified format.

        Args:
            input_path: Path to the source image file.
            output_path: Path where the converted image will be saved.
            output_format: Target format (png, jpg, webp, bmp, gif).
            options: Conversion options including:
                - quality: JPEG/WEBP quality (1-100, default 85)
                - optimize: Enable optimization (default True)
                - resize: Optional tuple (width, height) for resizing
            progress_callback: Optional callback function(progress, message).

        Returns:
            Path to the converted image file.

        Raises:
            ImageConversionError: If conversion fails.
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
            raise ImageConversionError(f"Input file not found: {input_path}")

        try:
            # Report progress: Loading
            if progress_callback:
                progress_callback(10, "Loading image")

            # Open and validate image
            image = self._load_image(input_path)

            # Report progress: Processing
            if progress_callback:
                progress_callback(30, "Processing image")

            # Apply resize if requested
            resize_dims = options.get("resize")
            if resize_dims:
                image = self._resize_image(image, resize_dims)

            # Handle transparency for non-transparent formats
            if output_format in NON_TRANSPARENT_FORMATS:
                image = self._handle_transparency(image, options)

            # Report progress: Converting
            if progress_callback:
                progress_callback(60, f"Converting to {output_format.upper()}")

            # Get the format handler and save
            handler = self._format_handlers.get(output_format)
            if not handler:
                raise ValueError(f"No handler for format: {output_format}")

            handler(image, output_path, options)

            # Report progress: Complete
            if progress_callback:
                progress_callback(100, "Conversion complete")

            logger.info(f"Successfully converted {input_path} to {output_path}")
            return output_path

        except Image.UnidentifiedImageError as e:
            logger.error(f"Cannot identify image file: {input_path}")
            raise ImageConversionError(f"Invalid or corrupted image file: {e}")
        except MemoryError:
            logger.error(f"Memory error processing image: {input_path}")
            raise ImageConversionError("Image too large to process")
        except Exception as e:
            logger.error(f"Image conversion failed: {e}")
            raise ImageConversionError(f"Conversion failed: {e}")

    def _load_image(self, path: Path) -> Image.Image:
        """
        Load and validate an image file.

        Args:
            path: Path to the image file.

        Returns:
            Loaded PIL Image object.

        Raises:
            ImageConversionError: If image cannot be loaded or is too large.
        """
        image = Image.open(path)

        # Validate dimensions
        width, height = image.size
        if width > MAX_DIMENSION or height > MAX_DIMENSION:
            raise ImageConversionError(
                f"Image dimensions ({width}x{height}) exceed maximum "
                f"allowed ({MAX_DIMENSION}x{MAX_DIMENSION})"
            )

        # Load image data into memory
        image.load()

        return image

    def _resize_image(
        self,
        image: Image.Image,
        dimensions: tuple
    ) -> Image.Image:
        """
        Resize an image to the specified dimensions.

        Args:
            image: Source PIL Image.
            dimensions: Target (width, height) tuple.

        Returns:
            Resized PIL Image.
        """
        width, height = dimensions

        # Validate dimensions
        if width <= 0 or height <= 0:
            raise ValueError("Resize dimensions must be positive")
        if width > MAX_DIMENSION or height > MAX_DIMENSION:
            raise ValueError(f"Resize dimensions exceed maximum: {MAX_DIMENSION}")

        # Use high-quality resampling
        return image.resize((width, height), Image.Resampling.LANCZOS)

    def _handle_transparency(
        self,
        image: Image.Image,
        options: Dict[str, Any]
    ) -> Image.Image:
        """
        Handle transparency for formats that don't support it.

        Converts RGBA to RGB with a configurable background color.

        Args:
            image: Source PIL Image.
            options: Options including 'background_color' (default white).

        Returns:
            Image with transparency removed.
        """
        if image.mode in ("RGBA", "LA", "P"):
            # Get background color from options or default to white
            bg_color = options.get("background_color", (255, 255, 255))

            # Handle palette mode with transparency
            if image.mode == "P" and "transparency" in image.info:
                image = image.convert("RGBA")

            if image.mode in ("RGBA", "LA"):
                # Create background image
                background = Image.new("RGB", image.size, bg_color)

                # Handle LA mode (grayscale with alpha)
                if image.mode == "LA":
                    image = image.convert("RGBA")

                # Composite the image onto the background
                background.paste(image, mask=image.split()[-1])
                return background

        # Convert other modes to RGB
        if image.mode not in ("RGB", "L"):
            return image.convert("RGB")

        return image

    def _save_as_png(
        self,
        image: Image.Image,
        output_path: Path,
        options: Dict[str, Any]
    ) -> None:
        """Save image as PNG format."""
        optimize = options.get("optimize", True)
        compress_level = options.get("compress_level", 6)

        # Ensure proper mode
        if image.mode not in ("RGB", "RGBA", "L", "LA", "P"):
            image = image.convert("RGBA")

        image.save(
            output_path,
            format="PNG",
            optimize=optimize,
            compress_level=compress_level
        )

    def _save_as_jpeg(
        self,
        image: Image.Image,
        output_path: Path,
        options: Dict[str, Any]
    ) -> None:
        """Save image as JPEG format."""
        quality = self._validate_quality(options.get("quality", DEFAULT_QUALITY))
        optimize = options.get("optimize", True)
        progressive = options.get("progressive", False)

        # Ensure RGB mode
        if image.mode not in ("RGB", "L"):
            image = image.convert("RGB")

        image.save(
            output_path,
            format="JPEG",
            quality=quality,
            optimize=optimize,
            progressive=progressive
        )

    def _save_as_webp(
        self,
        image: Image.Image,
        output_path: Path,
        options: Dict[str, Any]
    ) -> None:
        """Save image as WebP format."""
        quality = self._validate_quality(options.get("quality", DEFAULT_QUALITY))
        lossless = options.get("lossless", False)

        # Ensure proper mode
        if image.mode not in ("RGB", "RGBA", "L", "LA"):
            image = image.convert("RGBA")

        image.save(
            output_path,
            format="WEBP",
            quality=quality,
            lossless=lossless
        )

    def _save_as_bmp(
        self,
        image: Image.Image,
        output_path: Path,
        options: Dict[str, Any]
    ) -> None:
        """Save image as BMP format."""
        # Ensure RGB mode (BMP doesn't support alpha)
        if image.mode not in ("RGB", "L"):
            image = image.convert("RGB")

        image.save(output_path, format="BMP")

    def _save_as_gif(
        self,
        image: Image.Image,
        output_path: Path,
        options: Dict[str, Any]
    ) -> None:
        """Save image as GIF format."""
        optimize = options.get("optimize", True)

        # Convert to palette mode for GIF
        if image.mode == "RGBA":
            # Preserve transparency
            image.save(
                output_path,
                format="GIF",
                optimize=optimize,
                transparency=0
            )
        else:
            if image.mode != "P":
                image = image.convert("P", palette=Image.Palette.ADAPTIVE)
            image.save(output_path, format="GIF", optimize=optimize)

    @staticmethod
    def _validate_quality(quality: Any) -> int:
        """
        Validate and normalize quality parameter.

        Args:
            quality: Quality value to validate.

        Returns:
            Validated quality value between MIN_QUALITY and MAX_QUALITY.
        """
        try:
            quality = int(quality)
        except (ValueError, TypeError):
            return DEFAULT_QUALITY

        return max(MIN_QUALITY, min(MAX_QUALITY, quality))

    def get_image_info(self, path: Path) -> Dict[str, Any]:
        """
        Get information about an image file.

        Args:
            path: Path to the image file.

        Returns:
            Dictionary with image information.
        """
        try:
            with Image.open(path) as image:
                return {
                    "format": image.format,
                    "mode": image.mode,
                    "width": image.width,
                    "height": image.height,
                    "has_transparency": image.mode in ("RGBA", "LA", "P"),
                    "is_animated": getattr(image, "is_animated", False),
                    "n_frames": getattr(image, "n_frames", 1),
                }
        except Exception as e:
            logger.error(f"Failed to get image info: {e}")
            return {}
