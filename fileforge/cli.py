"""
FileForge CLI - Universal File Converter

A powerful command-line tool for converting files between various formats.
Supports images, documents, and data files with beautiful terminal output.

Usage:
    fileforge convert input.jpg output.png --quality 90
    fileforge list-formats
    fileforge interactive
"""

import sys
import time
from pathlib import Path
from typing import Optional, List, Tuple, Callable
from glob import glob

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    TimeRemainingColumn,
    TimeElapsedColumn,
)
from rich.prompt import Prompt, Confirm, IntPrompt
from rich.text import Text
from rich.style import Style
from rich import box
from rich.markdown import Markdown

# Import converters from the converters module
from fileforge.converters import (
    ImageConverter,
    DocumentConverter,
    DataConverter,
    get_supported_formats,
)


# Constants
VERSION = "1.0.0"
APP_NAME = "FileForge"

# Rich console instance for all output
console = Console()


# =============================================================================
# Utility Functions
# =============================================================================

def get_file_extension(file_path: str) -> str:
    """Extract file extension from path, lowercase and without dot."""
    return Path(file_path).suffix.lower().lstrip(".")


def get_file_size_human(file_path: str) -> str:
    """Get human-readable file size."""
    try:
        size = Path(file_path).stat().st_size
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} PB"
    except (OSError, FileNotFoundError):
        return "Unknown"


def validate_input_file(file_path: str) -> Tuple[bool, str]:
    """
    Validate that input file exists and is readable.

    Returns:
        Tuple of (is_valid, error_message)
    """
    path = Path(file_path)

    if not path.exists():
        return False, f"Input file not found: {file_path}"

    if not path.is_file():
        return False, f"Path is not a file: {file_path}"

    try:
        with open(path, "rb") as f:
            f.read(1)
        return True, ""
    except PermissionError:
        return False, f"Permission denied reading file: {file_path}"
    except Exception as e:
        return False, f"Cannot read file: {file_path} - {str(e)}"


def validate_output_path(file_path: str) -> Tuple[bool, str]:
    """
    Validate that output path is writable.

    Returns:
        Tuple of (is_valid, error_message)
    """
    path = Path(file_path)
    parent = path.parent

    if not parent.exists():
        try:
            parent.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            return False, f"Cannot create output directory: {parent}"
        except Exception as e:
            return False, f"Error creating output directory: {parent} - {str(e)}"

    if path.exists() and not path.is_file():
        return False, f"Output path exists and is not a file: {file_path}"

    return True, ""


def expand_glob_pattern(pattern: str) -> List[str]:
    """
    Expand glob pattern to list of matching files.

    Args:
        pattern: Glob pattern like '*.jpg' or 'images/*.png'

    Returns:
        List of matching file paths
    """
    matches = glob(pattern, recursive=True)
    # Filter to only files
    return [m for m in matches if Path(m).is_file()]


def determine_converter_type(input_ext: str, output_ext: str) -> Optional[str]:
    """
    Determine which converter to use based on file extensions.

    Returns:
        'image', 'document', 'data', or None if unsupported
    """
    image_formats = {"jpg", "jpeg", "png", "gif", "bmp", "webp", "tiff", "ico", "svg"}
    document_formats = {"pdf", "txt", "docx", "doc", "rtf", "html", "md"}
    data_formats = {"json", "csv", "xml", "yaml", "yml", "toml", "xlsx", "xls"}

    input_ext = input_ext.lower()
    output_ext = output_ext.lower()

    # Image conversion
    if input_ext in image_formats and output_ext in image_formats:
        return "image"

    # Document conversion
    if input_ext in document_formats or output_ext in document_formats:
        return "document"

    # Data conversion
    if input_ext in data_formats and output_ext in data_formats:
        return "data"

    return None


def display_error(message: str, suggestion: Optional[str] = None) -> None:
    """Display a formatted error message with optional suggestion."""
    error_text = Text()
    error_text.append("[ERROR] ", style="bold red")
    error_text.append(message, style="red")

    console.print()
    console.print(Panel(
        error_text,
        title="Error",
        title_align="left",
        border_style="red",
        box=box.ROUNDED,
    ))

    if suggestion:
        console.print()
        suggestion_text = Text()
        suggestion_text.append("[TIP] ", style="bold yellow")
        suggestion_text.append(suggestion, style="yellow")
        console.print(suggestion_text)


def display_success(message: str) -> None:
    """Display a formatted success message."""
    success_text = Text()
    success_text.append("[SUCCESS] ", style="bold green")
    success_text.append(message, style="green")
    console.print(success_text)


def display_warning(message: str) -> None:
    """Display a formatted warning message."""
    warning_text = Text()
    warning_text.append("[WARNING] ", style="bold yellow")
    warning_text.append(message, style="yellow")
    console.print(warning_text)


def display_info(message: str) -> None:
    """Display a formatted info message."""
    info_text = Text()
    info_text.append("[INFO] ", style="bold cyan")
    info_text.append(message, style="cyan")
    console.print(info_text)


def create_progress_bar() -> Progress:
    """Create a Rich progress bar with standard styling."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(bar_width=40),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        console=console,
        transient=False,
    )


# =============================================================================
# Conversion Statistics
# =============================================================================

class ConversionStats:
    """Track and display conversion statistics."""

    def __init__(self):
        self.total_files = 0
        self.successful = 0
        self.failed = 0
        self.skipped = 0
        self.total_input_size = 0
        self.total_output_size = 0
        self.start_time = None
        self.end_time = None
        self.errors: List[Tuple[str, str]] = []

    def start(self) -> None:
        """Mark the start of conversion."""
        self.start_time = time.time()

    def stop(self) -> None:
        """Mark the end of conversion."""
        self.end_time = time.time()

    @property
    def elapsed_time(self) -> float:
        """Get elapsed time in seconds."""
        if self.start_time is None:
            return 0.0
        end = self.end_time if self.end_time else time.time()
        return end - self.start_time

    @property
    def elapsed_time_human(self) -> str:
        """Get human-readable elapsed time."""
        seconds = self.elapsed_time
        if seconds < 60:
            return f"{seconds:.2f} seconds"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            secs = seconds % 60
            return f"{minutes}m {secs:.1f}s"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            return f"{hours}h {minutes}m"

    def add_success(self, input_size: int, output_size: int) -> None:
        """Record a successful conversion."""
        self.successful += 1
        self.total_input_size += input_size
        self.total_output_size += output_size

    def add_failure(self, file_path: str, error: str) -> None:
        """Record a failed conversion."""
        self.failed += 1
        self.errors.append((file_path, error))

    def add_skipped(self) -> None:
        """Record a skipped file."""
        self.skipped += 1

    def display(self) -> None:
        """Display conversion statistics as a Rich panel."""
        console.print()

        # Create statistics table
        stats_table = Table(show_header=False, box=box.SIMPLE)
        stats_table.add_column("Metric", style="bold")
        stats_table.add_column("Value", justify="right")

        stats_table.add_row("Total Files", str(self.total_files))
        stats_table.add_row(
            "Successful",
            Text(str(self.successful), style="green")
        )

        if self.failed > 0:
            stats_table.add_row(
                "Failed",
                Text(str(self.failed), style="red")
            )

        if self.skipped > 0:
            stats_table.add_row(
                "Skipped",
                Text(str(self.skipped), style="yellow")
            )

        stats_table.add_row("Time Elapsed", self.elapsed_time_human)

        if self.total_input_size > 0:
            input_size = self._format_size(self.total_input_size)
            output_size = self._format_size(self.total_output_size)
            ratio = (self.total_output_size / self.total_input_size) * 100

            stats_table.add_row("Input Size", input_size)
            stats_table.add_row("Output Size", output_size)
            stats_table.add_row("Size Ratio", f"{ratio:.1f}%")

        # Determine panel style based on results
        if self.failed == 0 and self.successful > 0:
            panel_style = "green"
            title = "Conversion Complete"
        elif self.successful > 0:
            panel_style = "yellow"
            title = "Conversion Complete with Errors"
        else:
            panel_style = "red"
            title = "Conversion Failed"

        console.print(Panel(
            stats_table,
            title=title,
            title_align="left",
            border_style=panel_style,
            box=box.ROUNDED,
        ))

        # Display errors if any
        if self.errors:
            console.print()
            error_table = Table(
                title="Errors",
                box=box.ROUNDED,
                border_style="red",
            )
            error_table.add_column("File", style="bold")
            error_table.add_column("Error", style="red")

            for file_path, error in self.errors[:10]:  # Show first 10 errors
                error_table.add_row(
                    Path(file_path).name,
                    error[:50] + "..." if len(error) > 50 else error
                )

            if len(self.errors) > 10:
                error_table.add_row(
                    f"... and {len(self.errors) - 10} more",
                    "",
                    style="dim"
                )

            console.print(error_table)

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """Format bytes as human-readable size."""
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} PB"


# =============================================================================
# Conversion Functions
# =============================================================================

def convert_single_file(
    input_path: str,
    output_path: str,
    quality: int = 85,
    width: Optional[int] = None,
    height: Optional[int] = None,
    scale: Optional[float] = None,
    pretty: bool = True,
    progress_callback: Optional[Callable[[float], None]] = None,
) -> Tuple[bool, str]:
    """
    Convert a single file from input format to output format.

    Args:
        input_path: Path to input file
        output_path: Path to output file
        quality: Quality for image conversion (1-100)
        width: Target width for image resize
        height: Target height for image resize
        scale: Scale factor for image resize
        pretty: Pretty print for data formats
        progress_callback: Callback function for progress updates

    Returns:
        Tuple of (success, error_message)
    """
    input_ext = get_file_extension(input_path)
    output_ext = get_file_extension(output_path)

    converter_type = determine_converter_type(input_ext, output_ext)

    if converter_type is None:
        return False, f"Unsupported conversion: {input_ext} -> {output_ext}"

    try:
        if converter_type == "image":
            converter = ImageConverter()
            converter.convert(
                input_path=input_path,
                output_path=output_path,
                quality=quality,
                width=width,
                height=height,
                scale=scale,
                progress_callback=progress_callback,
            )

        elif converter_type == "document":
            converter = DocumentConverter()

            # Handle specific document conversions
            if input_ext == "pdf" and output_ext == "txt":
                converter.pdf_to_text(
                    input_path=input_path,
                    output_path=output_path,
                    progress_callback=progress_callback,
                )
            elif input_ext == "pdf" and output_ext in ("png", "jpg", "jpeg"):
                # For PDF to images, output_path is treated as directory
                output_dir = str(Path(output_path).parent)
                converter.pdf_to_images(
                    input_path=input_path,
                    output_dir=output_dir,
                    progress_callback=progress_callback,
                )
            else:
                return False, f"Document conversion not supported: {input_ext} -> {output_ext}"

        elif converter_type == "data":
            converter = DataConverter()
            converter.convert(
                input_path=input_path,
                output_path=output_path,
                pretty=pretty,
                progress_callback=progress_callback,
            )

        return True, ""

    except FileNotFoundError as e:
        return False, f"File not found: {str(e)}"
    except PermissionError as e:
        return False, f"Permission denied: {str(e)}"
    except ValueError as e:
        return False, f"Invalid value: {str(e)}"
    except Exception as e:
        return False, f"Conversion error: {str(e)}"


# =============================================================================
# Click CLI Commands
# =============================================================================

@click.group(invoke_without_command=True)
@click.option("--version", "-v", is_flag=True, help="Show version and exit.")
@click.option("--formats", "-f", is_flag=True, help="List supported formats and exit.")
@click.pass_context
def cli(ctx: click.Context, version: bool, formats: bool) -> None:
    """
    FileForge - Universal File Converter

    A powerful CLI tool for converting files between various formats.
    Supports images, documents, and data files.

    \b
    Examples:
        fileforge convert input.jpg output.png
        fileforge convert *.jpg ./output/ --quality 90
        fileforge --formats
        fileforge interactive
    """
    if version:
        console.print(Panel(
            f"[bold cyan]{APP_NAME}[/bold cyan] version [bold green]{VERSION}[/bold green]\n\n"
            "A universal file converter supporting images, documents, and data files.",
            title="FileForge",
            border_style="cyan",
        ))
        ctx.exit(0)

    if formats:
        # Show supported formats table
        fmt_info = get_supported_formats()
        table = Table(
            title="[bold cyan]Supported Format Conversions[/bold cyan]",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold magenta",
        )
        table.add_column("Category", style="bold cyan", width=10)
        table.add_column("Input Formats", style="green")
        table.add_column("Output Formats", style="blue")

        for category, info in fmt_info.items():
            table.add_row(
                category.capitalize(),
                ", ".join(info.get("input", [])),
                ", ".join(info.get("output", [])),
            )

        console.print()
        console.print(table)
        console.print()
        ctx.exit(0)

    if ctx.invoked_subcommand is None:
        # Show help if no command provided
        console.print()
        console.print(Panel(
            Markdown("""
# FileForge - Universal File Converter

A powerful CLI tool for converting files between various formats.

## Quick Start

```bash
# Convert a single file
fileforge convert input.jpg output.png

# Batch convert with wildcards
fileforge convert "*.jpg" ./output/ --quality 90

# List supported formats
fileforge list-formats

# Interactive mode
fileforge interactive
```

## Commands

- **convert** - Convert files between formats
- **list-formats** - Show supported format conversions
- **interactive** - Start interactive conversion wizard

Use `fileforge COMMAND --help` for more information on a command.
            """),
            title=f"{APP_NAME} v{VERSION}",
            border_style="cyan",
            box=box.DOUBLE,
        ))


@cli.command("convert")
@click.argument("input_path", type=str)
@click.argument("output_path", type=str)
@click.option(
    "--quality", "-q",
    type=click.IntRange(1, 100),
    default=85,
    help="Quality for image conversion (1-100). Default: 85"
)
@click.option(
    "--width", "-w",
    type=int,
    default=None,
    help="Target width for image resize (preserves aspect ratio if height not set)"
)
@click.option(
    "--height", "-h",
    type=int,
    default=None,
    help="Target height for image resize (preserves aspect ratio if width not set)"
)
@click.option(
    "--scale", "-s",
    type=float,
    default=None,
    help="Scale factor for image resize (e.g., 0.5 for half size, 2.0 for double)"
)
@click.option(
    "--pretty/--no-pretty",
    default=True,
    help="Pretty print output for data formats. Default: True"
)
@click.option(
    "--overwrite", "-o",
    is_flag=True,
    default=False,
    help="Overwrite existing output files without prompting"
)
@click.option(
    "--verbose", "-V",
    is_flag=True,
    default=False,
    help="Show verbose output during conversion"
)
def convert_command(
    input_path: str,
    output_path: str,
    quality: int,
    width: Optional[int],
    height: Optional[int],
    scale: Optional[float],
    pretty: bool,
    overwrite: bool,
    verbose: bool,
) -> None:
    """
    Convert files between formats.

    \b
    INPUT_PATH can be:
      - A single file: input.jpg
      - A glob pattern: *.jpg, images/*.png

    \b
    OUTPUT_PATH can be:
      - A single file: output.png (for single input)
      - A directory: ./output/ (for batch conversion)

    \b
    Examples:
        fileforge convert photo.jpg photo.png
        fileforge convert photo.jpg photo.webp --quality 80
        fileforge convert photo.jpg resized.jpg --width 800
        fileforge convert photo.jpg scaled.jpg --scale 0.5
        fileforge convert "*.jpg" ./converted/ --quality 90
        fileforge convert data.json data.csv
        fileforge convert document.pdf text.txt
    """
    console.print()

    # Expand glob patterns for input
    if "*" in input_path or "?" in input_path:
        input_files = expand_glob_pattern(input_path)
        if not input_files:
            display_error(
                f"No files found matching pattern: {input_path}",
                "Check the pattern and ensure files exist in the specified location."
            )
            sys.exit(1)

        display_info(f"Found {len(input_files)} file(s) matching pattern")
        is_batch = True
    else:
        # Single file
        valid, error = validate_input_file(input_path)
        if not valid:
            display_error(error, "Check the file path and permissions.")
            sys.exit(1)
        input_files = [input_path]
        is_batch = False

    # Determine output handling
    output_path_obj = Path(output_path)

    if is_batch:
        # For batch conversion, output must be a directory
        if not output_path.endswith("/") and not output_path_obj.is_dir():
            # Create directory if it looks like one
            if "." not in output_path_obj.name:
                output_path_obj.mkdir(parents=True, exist_ok=True)
            else:
                display_error(
                    "For batch conversion, output must be a directory.",
                    f"Use: fileforge convert \"{input_path}\" ./output_folder/"
                )
                sys.exit(1)
        elif not output_path_obj.exists():
            output_path_obj.mkdir(parents=True, exist_ok=True)

    # Initialize statistics
    stats = ConversionStats()
    stats.total_files = len(input_files)
    stats.start()

    # Process files
    with create_progress_bar() as progress:
        overall_task = progress.add_task(
            "[cyan]Converting files...",
            total=len(input_files)
        )

        for input_file in input_files:
            input_name = Path(input_file).name

            # Determine output file path
            if is_batch:
                # Get extension from first file or use same as input
                output_ext = get_file_extension(input_files[0])
                # If output_path has an extension hint (folder.png style), use it
                if "." in output_path_obj.name:
                    output_ext = get_file_extension(output_path)
                    output_dir = output_path_obj.parent
                else:
                    output_dir = output_path_obj
                    # Keep same extension as input
                    output_ext = get_file_extension(input_file)

                output_file = str(
                    output_dir / f"{Path(input_file).stem}.{output_ext}"
                )
            else:
                output_file = output_path

            # Check if output exists
            if Path(output_file).exists() and not overwrite:
                if not is_batch:
                    if not Confirm.ask(
                        f"[yellow]Output file exists: {output_file}. Overwrite?[/yellow]"
                    ):
                        display_warning("Conversion cancelled by user.")
                        sys.exit(0)
                else:
                    # In batch mode, skip existing unless overwrite flag
                    if verbose:
                        display_warning(f"Skipping existing file: {output_file}")
                    stats.add_skipped()
                    progress.update(overall_task, advance=1)
                    continue

            # Validate output path
            valid, error = validate_output_path(output_file)
            if not valid:
                stats.add_failure(input_file, error)
                progress.update(overall_task, advance=1)
                continue

            # Create progress callback for individual file
            file_task = None
            if verbose:
                file_task = progress.add_task(
                    f"[blue]{input_name}",
                    total=100
                )

            def progress_callback(percent: float) -> None:
                if file_task is not None:
                    progress.update(file_task, completed=percent)

            # Perform conversion
            if verbose:
                display_info(f"Converting: {input_name}")

            success, error = convert_single_file(
                input_path=input_file,
                output_path=output_file,
                quality=quality,
                width=width,
                height=height,
                scale=scale,
                pretty=pretty,
                progress_callback=progress_callback if verbose else None,
            )

            if success:
                input_size = Path(input_file).stat().st_size
                output_size = Path(output_file).stat().st_size if Path(output_file).exists() else 0
                stats.add_success(input_size, output_size)

                if verbose:
                    display_success(f"Converted: {input_name} -> {Path(output_file).name}")
            else:
                stats.add_failure(input_file, error)
                if verbose:
                    display_error(f"Failed: {input_name} - {error}")

            if file_task is not None:
                progress.remove_task(file_task)

            progress.update(overall_task, advance=1)

    # Finalize and display stats
    stats.stop()
    stats.display()

    # Exit with appropriate code
    if stats.failed > 0 and stats.successful == 0:
        sys.exit(1)
    elif stats.failed > 0:
        sys.exit(2)  # Partial success


@cli.command("list-formats")
@click.option(
    "--type", "-t",
    type=click.Choice(["all", "image", "document", "data"]),
    default="all",
    help="Filter formats by type"
)
def list_formats_command(type: str) -> None:
    """
    Display all supported file format conversions.

    Shows a table of supported input and output formats organized by category.

    \b
    Examples:
        fileforge list-formats
        fileforge list-formats --type image
        fileforge list-formats -t data
    """
    console.print()

    # Get format information from converters module
    try:
        formats = get_supported_formats()
    except Exception:
        # Fallback to hardcoded formats if function not available
        formats = {
            "image": {
                "input": ["jpg", "jpeg", "png", "gif", "bmp", "webp", "tiff", "ico", "svg"],
                "output": ["jpg", "jpeg", "png", "gif", "bmp", "webp", "tiff", "ico"],
                "description": "Image file formats",
            },
            "document": {
                "input": ["pdf", "docx", "doc", "rtf", "html", "md"],
                "output": ["txt", "pdf", "html", "md", "png", "jpg"],
                "description": "Document file formats",
            },
            "data": {
                "input": ["json", "csv", "xml", "yaml", "yml", "toml", "xlsx"],
                "output": ["json", "csv", "xml", "yaml", "toml"],
                "description": "Data and configuration formats",
            },
        }

    # Filter by type if specified
    if type != "all":
        formats = {k: v for k, v in formats.items() if k == type}

    # Create main table
    table = Table(
        title="[bold cyan]Supported Format Conversions[/bold cyan]",
        box=box.DOUBLE_EDGE,
        show_header=True,
        header_style="bold magenta",
    )

    table.add_column("Category", style="bold cyan", width=12)
    table.add_column("Input Formats", style="green")
    table.add_column("Output Formats", style="blue")
    table.add_column("Description", style="dim")

    for category, info in formats.items():
        input_fmts = ", ".join(info.get("input", []))
        output_fmts = ", ".join(info.get("output", []))
        description = info.get("description", "")

        table.add_row(
            category.capitalize(),
            input_fmts,
            output_fmts,
            description,
        )

    console.print(table)
    console.print()

    # Show usage examples
    examples_panel = Panel(
        Markdown("""
## Usage Examples

**Image Conversion:**
```bash
fileforge convert photo.jpg photo.png
fileforge convert image.png image.webp --quality 85
fileforge convert large.jpg small.jpg --scale 0.5
```

**Document Conversion:**
```bash
fileforge convert document.pdf text.txt
fileforge convert report.pdf ./images/
```

**Data Conversion:**
```bash
fileforge convert data.json data.csv
fileforge convert config.yaml config.json --pretty
```
        """),
        title="Examples",
        border_style="dim",
    )
    console.print(examples_panel)


@cli.command("interactive")
def interactive_command() -> None:
    """
    Start the interactive conversion wizard.

    Guides you through the conversion process step by step with prompts
    for input file, output format, and conversion options.
    """
    console.print()
    console.print(Panel(
        "[bold cyan]Interactive Conversion Wizard[/bold cyan]\n\n"
        "This wizard will guide you through the file conversion process.\n"
        "Press Ctrl+C at any time to cancel.",
        title=f"{APP_NAME}",
        border_style="cyan",
    ))
    console.print()

    try:
        # Step 1: Get input file
        console.print("[bold]Step 1: Select Input File[/bold]")
        while True:
            input_path = Prompt.ask(
                "[cyan]Enter the path to your input file[/cyan]"
            )

            valid, error = validate_input_file(input_path)
            if valid:
                break
            display_error(error)

        input_ext = get_file_extension(input_path)
        input_size = get_file_size_human(input_path)

        display_success(f"Selected: {Path(input_path).name} ({input_size})")
        console.print()

        # Step 2: Determine conversion type and show options
        console.print("[bold]Step 2: Select Output Format[/bold]")

        # Get available output formats based on input
        converter_type = None
        output_formats = []

        image_formats = ["jpg", "jpeg", "png", "gif", "bmp", "webp", "tiff", "ico"]
        document_formats = ["txt", "pdf", "html", "md", "png", "jpg"]
        data_formats = ["json", "csv", "xml", "yaml", "toml"]

        if input_ext in ["jpg", "jpeg", "png", "gif", "bmp", "webp", "tiff", "ico", "svg"]:
            converter_type = "image"
            output_formats = [f for f in image_formats if f != input_ext]
        elif input_ext in ["pdf", "docx", "doc", "rtf", "html", "md"]:
            converter_type = "document"
            output_formats = document_formats
        elif input_ext in ["json", "csv", "xml", "yaml", "yml", "toml", "xlsx"]:
            converter_type = "data"
            output_formats = [f for f in data_formats if f != input_ext]
        else:
            display_error(
                f"Unsupported input format: {input_ext}",
                "Use 'fileforge list-formats' to see supported formats."
            )
            sys.exit(1)

        # Display format options
        format_table = Table(show_header=False, box=box.SIMPLE)
        format_table.add_column("Number", style="cyan", width=4)
        format_table.add_column("Format", style="bold")

        for i, fmt in enumerate(output_formats, 1):
            format_table.add_row(str(i), fmt.upper())

        console.print(format_table)

        while True:
            choice = IntPrompt.ask(
                f"[cyan]Select output format (1-{len(output_formats)})[/cyan]",
                default=1
            )
            if 1 <= choice <= len(output_formats):
                output_ext = output_formats[choice - 1]
                break
            display_error(f"Please enter a number between 1 and {len(output_formats)}")

        console.print()

        # Step 3: Get output path
        console.print("[bold]Step 3: Specify Output Location[/bold]")

        # Suggest default output path
        default_output = str(Path(input_path).with_suffix(f".{output_ext}"))

        output_path = Prompt.ask(
            "[cyan]Enter output file path[/cyan]",
            default=default_output
        )

        # Validate output path
        valid, error = validate_output_path(output_path)
        if not valid:
            display_error(error)
            sys.exit(1)

        # Check if file exists
        if Path(output_path).exists():
            if not Confirm.ask(
                "[yellow]Output file exists. Overwrite?[/yellow]",
                default=False
            ):
                display_warning("Conversion cancelled.")
                sys.exit(0)

        console.print()

        # Step 4: Conversion options (for images)
        quality = 85
        width = None
        height = None
        scale = None
        pretty = True

        if converter_type == "image":
            console.print("[bold]Step 4: Conversion Options[/bold]")

            # Quality
            quality = IntPrompt.ask(
                "[cyan]Image quality (1-100)[/cyan]",
                default=85
            )
            quality = max(1, min(100, quality))

            # Resize options
            if Confirm.ask("[cyan]Do you want to resize the image?[/cyan]", default=False):
                resize_choice = Prompt.ask(
                    "[cyan]Resize by (w)idth, (h)eight, or (s)cale?[/cyan]",
                    choices=["w", "h", "s"],
                    default="s"
                )

                if resize_choice == "w":
                    width = IntPrompt.ask("[cyan]Target width (pixels)[/cyan]")
                elif resize_choice == "h":
                    height = IntPrompt.ask("[cyan]Target height (pixels)[/cyan]")
                else:
                    scale = float(Prompt.ask(
                        "[cyan]Scale factor (e.g., 0.5 for half, 2.0 for double)[/cyan]",
                        default="1.0"
                    ))

            console.print()

        elif converter_type == "data":
            console.print("[bold]Step 4: Conversion Options[/bold]")
            pretty = Confirm.ask(
                "[cyan]Pretty print output?[/cyan]",
                default=True
            )
            console.print()

        # Step 5: Confirm and convert
        console.print("[bold]Step 5: Confirm Conversion[/bold]")

        confirm_table = Table(show_header=False, box=box.ROUNDED)
        confirm_table.add_column("Setting", style="bold")
        confirm_table.add_column("Value")

        confirm_table.add_row("Input", str(input_path))
        confirm_table.add_row("Output", str(output_path))
        confirm_table.add_row("Conversion", f"{input_ext.upper()} -> {output_ext.upper()}")

        if converter_type == "image":
            confirm_table.add_row("Quality", str(quality))
            if width:
                confirm_table.add_row("Width", f"{width}px")
            if height:
                confirm_table.add_row("Height", f"{height}px")
            if scale:
                confirm_table.add_row("Scale", f"{scale}x")

        console.print(confirm_table)
        console.print()

        if not Confirm.ask("[cyan]Proceed with conversion?[/cyan]", default=True):
            display_warning("Conversion cancelled.")
            sys.exit(0)

        console.print()

        # Perform conversion
        stats = ConversionStats()
        stats.total_files = 1
        stats.start()

        with create_progress_bar() as progress:
            task = progress.add_task("[cyan]Converting...", total=100)

            def progress_callback(percent: float) -> None:
                progress.update(task, completed=percent)

            success, error = convert_single_file(
                input_path=input_path,
                output_path=output_path,
                quality=quality,
                width=width,
                height=height,
                scale=scale,
                pretty=pretty,
                progress_callback=progress_callback,
            )

        if success:
            input_size = Path(input_path).stat().st_size
            output_size = Path(output_path).stat().st_size if Path(output_path).exists() else 0
            stats.add_success(input_size, output_size)
        else:
            stats.add_failure(input_path, error)

        stats.stop()
        stats.display()

        if not success:
            sys.exit(1)

    except KeyboardInterrupt:
        console.print()
        display_warning("Conversion cancelled by user.")
        sys.exit(130)


# =============================================================================
# Entry Point
# =============================================================================

def main() -> None:
    """Main entry point for the FileForge CLI."""
    try:
        cli()
    except KeyboardInterrupt:
        console.print()
        display_warning("Operation cancelled by user.")
        sys.exit(130)
    except Exception as e:
        display_error(
            f"An unexpected error occurred: {str(e)}",
            "Please report this issue at https://github.com/fileforge/fileforge/issues"
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
