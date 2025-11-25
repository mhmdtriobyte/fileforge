"""FileForge - Universal File Converter CLI.

A fast, offline universal file converter with a beautiful CLI interface.
Supports image, document, and data format conversions.
"""

__version__ = "1.0.0"
__author__ = "Mohammad Issa"

from fileforge.converters import (
    # Main converter classes
    ImageConverter,
    DocumentConverter,
    DataConverter,
    ConverterFactory,
    # Options dataclasses
    ImageConversionOptions,
    PDFConversionOptions,
    DataConversionOptions,
    # Format enums
    ImageFormat,
    DataFormat,
    # Result types
    ConversionResult,
    BatchConversionResult,
    ConversionStatus,
    ConversionStatistics,
    # Exceptions
    ConversionError,
    UnsupportedFormatError,
    InvalidInputError,
    OutputError,
    # Convenience functions
    convert_image,
    convert_pdf_to_text,
    convert_pdf_to_images,
    convert_data,
    batch_convert_images,
    batch_convert_data,
    get_supported_formats,
)

__all__ = [
    # Version info
    "__version__",
    "__author__",
    # Converter classes
    "ImageConverter",
    "DocumentConverter",
    "DataConverter",
    "ConverterFactory",
    # Options
    "ImageConversionOptions",
    "PDFConversionOptions",
    "DataConversionOptions",
    # Format enums
    "ImageFormat",
    "DataFormat",
    # Results
    "ConversionResult",
    "BatchConversionResult",
    "ConversionStatus",
    "ConversionStatistics",
    # Exceptions
    "ConversionError",
    "UnsupportedFormatError",
    "InvalidInputError",
    "OutputError",
    # Convenience functions
    "convert_image",
    "convert_pdf_to_text",
    "convert_pdf_to_images",
    "convert_data",
    "batch_convert_images",
    "batch_convert_data",
    "get_supported_formats",
]
