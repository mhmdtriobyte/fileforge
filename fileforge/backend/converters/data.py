"""
FileForge Data Converter

This module provides data file conversion functionality supporting CSV, JSON,
and Excel formats using pandas and openpyxl.
"""

import json
import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import pandas as pd

from utils import ConversionProgress

logger = logging.getLogger(__name__)

# Supported formats
SUPPORTED_INPUT_FORMATS = {"csv", "json", "xlsx", "xls"}
SUPPORTED_OUTPUT_FORMATS = {"csv", "json", "xlsx"}

# Processing limits
MAX_ROWS = 1_000_000
MAX_COLUMNS = 1000
MAX_FILE_SIZE_MB = 100


class DataConversionError(Exception):
    """Exception raised when data conversion fails."""
    pass


class DataConverter:
    """
    Handles data file conversions between CSV, JSON, and Excel formats
    using pandas for data manipulation.
    """

    def __init__(self):
        """Initialize the DataConverter."""
        self._readers: Dict[str, Callable] = {
            "csv": self._read_csv,
            "json": self._read_json,
            "xlsx": self._read_excel,
            "xls": self._read_excel,
        }
        self._writers: Dict[str, Callable] = {
            "csv": self._write_csv,
            "json": self._write_json,
            "xlsx": self._write_excel,
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
        Convert a data file to the specified format.

        Args:
            input_path: Path to the source data file.
            output_path: Path where the converted file will be saved.
            output_format: Target format (csv, json, xlsx).
            options: Conversion options including:
                - encoding: File encoding (default 'utf-8')
                - delimiter: CSV delimiter (default ',')
                - sheet_name: Excel sheet name (default 'Sheet1')
                - orient: JSON orientation ('records', 'columns', etc.)
                - index: Include index in output (default False)
            progress_callback: Optional callback function(progress, message).

        Returns:
            Path to the converted file.

        Raises:
            DataConversionError: If conversion fails.
            ValueError: If format is not supported.
        """
        options = options or {}
        output_format = output_format.lower().lstrip(".")
        input_format = input_path.suffix.lower().lstrip(".")

        # Validate formats
        if input_format not in SUPPORTED_INPUT_FORMATS:
            raise ValueError(
                f"Unsupported input format: {input_format}. "
                f"Supported formats: {SUPPORTED_INPUT_FORMATS}"
            )

        if output_format not in SUPPORTED_OUTPUT_FORMATS:
            raise ValueError(
                f"Unsupported output format: {output_format}. "
                f"Supported formats: {SUPPORTED_OUTPUT_FORMATS}"
            )

        if not input_path.exists():
            raise DataConversionError(f"Input file not found: {input_path}")

        # Check file size
        file_size_mb = input_path.stat().st_size / (1024 * 1024)
        if file_size_mb > MAX_FILE_SIZE_MB:
            raise DataConversionError(
                f"File size ({file_size_mb:.1f}MB) exceeds maximum ({MAX_FILE_SIZE_MB}MB)"
            )

        try:
            # Report progress: Reading
            if progress_callback:
                progress_callback(10, f"Reading {input_format.upper()} file")

            # Read the input file
            reader = self._readers.get(input_format)
            if not reader:
                raise ValueError(f"No reader for format: {input_format}")

            df = reader(input_path, options)

            # Validate data size
            self._validate_dataframe(df)

            # Report progress: Processing
            if progress_callback:
                progress_callback(50, "Processing data")

            # Apply any data transformations
            df = self._apply_transformations(df, options)

            # Report progress: Writing
            if progress_callback:
                progress_callback(75, f"Writing {output_format.upper()} file")

            # Ensure output path has correct extension
            expected_ext = f".{output_format}"
            if output_path.suffix.lower() != expected_ext:
                output_path = output_path.with_suffix(expected_ext)

            # Write the output file
            writer = self._writers.get(output_format)
            if not writer:
                raise ValueError(f"No writer for format: {output_format}")

            writer(df, output_path, options)

            # Report progress: Complete
            if progress_callback:
                progress_callback(100, "Conversion complete")

            logger.info(f"Successfully converted {input_path} to {output_path}")
            return output_path

        except pd.errors.EmptyDataError:
            raise DataConversionError("Input file is empty or contains no valid data")
        except pd.errors.ParserError as e:
            raise DataConversionError(f"Failed to parse input file: {e}")
        except Exception as e:
            logger.error(f"Data conversion failed: {e}")
            if isinstance(e, DataConversionError):
                raise
            raise DataConversionError(f"Conversion failed: {e}")

    def _validate_dataframe(self, df: pd.DataFrame) -> None:
        """
        Validate dataframe dimensions against limits.

        Args:
            df: DataFrame to validate.

        Raises:
            DataConversionError: If dataframe exceeds limits.
        """
        if len(df) > MAX_ROWS:
            raise DataConversionError(
                f"Data has {len(df)} rows, exceeds maximum of {MAX_ROWS}"
            )
        if len(df.columns) > MAX_COLUMNS:
            raise DataConversionError(
                f"Data has {len(df.columns)} columns, exceeds maximum of {MAX_COLUMNS}"
            )

    def _apply_transformations(
        self,
        df: pd.DataFrame,
        options: Dict[str, Any]
    ) -> pd.DataFrame:
        """
        Apply optional data transformations.

        Args:
            df: Input DataFrame.
            options: Transformation options.

        Returns:
            Transformed DataFrame.
        """
        # Drop empty rows if requested
        if options.get("drop_empty_rows", False):
            df = df.dropna(how="all")

        # Drop empty columns if requested
        if options.get("drop_empty_columns", False):
            df = df.dropna(axis=1, how="all")

        # Strip whitespace from string columns if requested
        if options.get("strip_whitespace", False):
            for col in df.select_dtypes(include=["object"]).columns:
                df[col] = df[col].str.strip()

        # Rename columns if mapping provided
        column_mapping = options.get("rename_columns")
        if column_mapping and isinstance(column_mapping, dict):
            df = df.rename(columns=column_mapping)

        # Select specific columns if provided
        selected_columns = options.get("columns")
        if selected_columns and isinstance(selected_columns, list):
            available_cols = [c for c in selected_columns if c in df.columns]
            if available_cols:
                df = df[available_cols]

        return df

    def _read_csv(self, path: Path, options: Dict[str, Any]) -> pd.DataFrame:
        """
        Read a CSV file into a DataFrame.

        Args:
            path: Path to the CSV file.
            options: Read options (encoding, delimiter, etc.).

        Returns:
            DataFrame with CSV data.
        """
        encoding = options.get("encoding", "utf-8")
        delimiter = options.get("delimiter", ",")
        header = options.get("header", 0)  # Row to use as header

        try:
            return pd.read_csv(
                path,
                encoding=encoding,
                delimiter=delimiter,
                header=header,
                low_memory=False,
                on_bad_lines="warn"
            )
        except UnicodeDecodeError:
            # Try with different encoding
            logger.warning(f"UTF-8 decode failed, trying latin-1 for {path}")
            return pd.read_csv(
                path,
                encoding="latin-1",
                delimiter=delimiter,
                header=header,
                low_memory=False,
                on_bad_lines="warn"
            )

    def _read_json(self, path: Path, options: Dict[str, Any]) -> pd.DataFrame:
        """
        Read a JSON file into a DataFrame.

        Args:
            path: Path to the JSON file.
            options: Read options (encoding, orient, etc.).

        Returns:
            DataFrame with JSON data.
        """
        encoding = options.get("encoding", "utf-8")
        orient = options.get("orient")

        # First, try to read the file and determine its structure
        with open(path, "r", encoding=encoding) as f:
            content = f.read()

        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            raise DataConversionError(f"Invalid JSON file: {e}")

        # Determine how to parse based on structure
        if isinstance(data, list):
            # Array of objects or values
            if orient:
                return pd.read_json(path, orient=orient, encoding=encoding)
            return pd.DataFrame(data)
        elif isinstance(data, dict):
            # Could be various orientations
            if orient:
                return pd.read_json(path, orient=orient, encoding=encoding)

            # Try to detect the structure
            first_value = next(iter(data.values()), None)
            if isinstance(first_value, list):
                # Likely columns orientation
                return pd.DataFrame(data)
            elif isinstance(first_value, dict):
                # Likely index orientation
                return pd.DataFrame.from_dict(data, orient="index")
            else:
                # Single row of data
                return pd.DataFrame([data])
        else:
            raise DataConversionError("JSON must be an object or array")

    def _read_excel(self, path: Path, options: Dict[str, Any]) -> pd.DataFrame:
        """
        Read an Excel file into a DataFrame.

        Args:
            path: Path to the Excel file.
            options: Read options (sheet_name, header, etc.).

        Returns:
            DataFrame with Excel data.
        """
        sheet_name = options.get("sheet_name", 0)  # First sheet by default
        header = options.get("header", 0)

        # Determine engine based on file extension
        ext = path.suffix.lower()
        engine = "openpyxl" if ext == ".xlsx" else "xlrd"

        try:
            return pd.read_excel(
                path,
                sheet_name=sheet_name,
                header=header,
                engine=engine
            )
        except ImportError as e:
            if "openpyxl" in str(e):
                raise DataConversionError(
                    "openpyxl is required for .xlsx files. Install with: pip install openpyxl"
                )
            elif "xlrd" in str(e):
                raise DataConversionError(
                    "xlrd is required for .xls files. Install with: pip install xlrd"
                )
            raise

    def _write_csv(
        self,
        df: pd.DataFrame,
        path: Path,
        options: Dict[str, Any]
    ) -> None:
        """
        Write a DataFrame to a CSV file.

        Args:
            df: DataFrame to write.
            path: Output file path.
            options: Write options (encoding, delimiter, index, etc.).
        """
        encoding = options.get("encoding", "utf-8")
        delimiter = options.get("delimiter", ",")
        include_index = options.get("index", False)

        df.to_csv(
            path,
            encoding=encoding,
            sep=delimiter,
            index=include_index
        )

    def _write_json(
        self,
        df: pd.DataFrame,
        path: Path,
        options: Dict[str, Any]
    ) -> None:
        """
        Write a DataFrame to a JSON file.

        Args:
            df: DataFrame to write.
            path: Output file path.
            options: Write options (orient, indent, etc.).
        """
        orient = options.get("orient", "records")
        indent = options.get("indent", 2)
        include_index = options.get("index", False)

        # Handle index based on orientation
        if orient in ("records", "values"):
            include_index = False

        df.to_json(
            path,
            orient=orient,
            indent=indent,
            index=include_index,
            force_ascii=False
        )

    def _write_excel(
        self,
        df: pd.DataFrame,
        path: Path,
        options: Dict[str, Any]
    ) -> None:
        """
        Write a DataFrame to an Excel file.

        Args:
            df: DataFrame to write.
            path: Output file path.
            options: Write options (sheet_name, index, etc.).
        """
        sheet_name = options.get("sheet_name", "Sheet1")
        include_index = options.get("index", False)
        freeze_panes = options.get("freeze_panes", (1, 0))  # Freeze header row

        with pd.ExcelWriter(path, engine="openpyxl") as writer:
            df.to_excel(
                writer,
                sheet_name=sheet_name,
                index=include_index,
                freeze_panes=freeze_panes
            )

    def get_data_info(self, path: Path) -> Dict[str, Any]:
        """
        Get information about a data file.

        Args:
            path: Path to the data file.

        Returns:
            Dictionary with data file information.
        """
        try:
            input_format = path.suffix.lower().lstrip(".")

            if input_format not in self._readers:
                return {"error": f"Unsupported format: {input_format}"}

            reader = self._readers[input_format]
            df = reader(path, {})

            # Get column info
            columns_info = []
            for col in df.columns:
                col_info = {
                    "name": str(col),
                    "dtype": str(df[col].dtype),
                    "non_null_count": int(df[col].count()),
                    "null_count": int(df[col].isna().sum()),
                }
                columns_info.append(col_info)

            return {
                "num_rows": len(df),
                "num_columns": len(df.columns),
                "columns": columns_info,
                "memory_usage_mb": df.memory_usage(deep=True).sum() / (1024 * 1024),
                "file_size_mb": path.stat().st_size / (1024 * 1024),
            }

        except Exception as e:
            logger.error(f"Failed to get data info: {e}")
            return {"error": str(e)}

    def get_preview(
        self,
        path: Path,
        num_rows: int = 10
    ) -> Dict[str, Any]:
        """
        Get a preview of the data file.

        Args:
            path: Path to the data file.
            num_rows: Number of rows to preview.

        Returns:
            Dictionary with preview data.
        """
        try:
            input_format = path.suffix.lower().lstrip(".")

            if input_format not in self._readers:
                return {"error": f"Unsupported format: {input_format}"}

            reader = self._readers[input_format]
            df = reader(path, {})

            # Get preview
            preview_df = df.head(num_rows)

            return {
                "columns": list(df.columns),
                "data": preview_df.to_dict(orient="records"),
                "total_rows": len(df),
                "preview_rows": len(preview_df),
            }

        except Exception as e:
            logger.error(f"Failed to get data preview: {e}")
            return {"error": str(e)}
