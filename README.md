# FileForge

Fast, offline universal file converter with a beautiful CLI interface.

## Features

- **Image Conversion**: PNG, JPG, WEBP, BMP, GIF with quality and resize options
- **Document Conversion**: PDF to text, PDF to images (page extraction)
- **Data Conversion**: CSV, JSON, Excel with formatting options
- **Beautiful Terminal UI**: Rich progress bars, tables, and colored output
- **Privacy-First**: Everything runs locally, no data leaves your machine
- **Cross-Platform**: Works on Windows, macOS, and Linux

## Installation

### From Source (Development)

```bash
git clone https://github.com/mhmdtriobyte/fileforge.git
cd fileforge
pip install -e .
```

### From PyPI (Coming Soon)

```bash
pip install fileforge
```

## Usage

### Convert Files

```bash
# Image conversion
fileforge convert photo.png photo.jpg
fileforge convert photo.png photo.webp --quality 90
fileforge convert photo.jpg resized.jpg --width 800 --height 600
fileforge convert photo.jpg scaled.jpg --scale 0.5

# Document conversion
fileforge convert document.pdf document.txt
fileforge convert document.pdf ./pages/ --format png

# Data conversion
fileforge convert data.csv data.json --pretty
fileforge convert data.json data.xlsx
fileforge convert spreadsheet.xlsx data.csv

# Batch conversion
fileforge convert "*.jpg" ./output/ --quality 85
```

### List Supported Formats

```bash
fileforge list-formats
fileforge list-formats --type image
fileforge list-formats --type document
fileforge list-formats --type data
```

### Interactive Mode

```bash
fileforge interactive
```

## Supported Conversions

| Type | Input Formats | Output Formats |
|------|---------------|----------------|
| Image | PNG, JPG, WEBP, BMP, GIF | PNG, JPG, WEBP, BMP, GIF |
| Document | PDF | TXT, PNG (page images) |
| Data | CSV, JSON, XLSX | CSV, JSON, XLSX |

## Options

### Image Options

- `--quality, -q`: Output quality for lossy formats (1-100, default: 85)
- `--width, -w`: Resize to specific width in pixels
- `--height, -h`: Resize to specific height in pixels
- `--scale, -s`: Scale by percentage (e.g., 0.5 for 50%)

### General Options

- `--overwrite, -o`: Overwrite existing output files
- `--verbose, -V`: Show detailed output
- `--pretty/--no-pretty`: Pretty format output (for JSON)

## Development

```bash
# Clone the repository
git clone https://github.com/mhmdtriobyte/fileforge.git
cd fileforge

# Install in development mode with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black fileforge/
ruff check fileforge/
```

## License

MIT License - see [LICENSE](LICENSE) for details.
