# FileForge

A modern, professional file converter web application built with FastAPI and React.

![FileForge](https://img.shields.io/badge/FileForge-v2.0-blue?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.9+-green?style=flat-square&logo=python)
![React](https://img.shields.io/badge/React-18-blue?style=flat-square&logo=react)
![TypeScript](https://img.shields.io/badge/TypeScript-5.6-blue?style=flat-square&logo=typescript)

## Features

- **Drag & Drop Upload** - Simply drag files onto the drop zone or click to browse
- **Multiple File Support** - Convert multiple files at once
- **Auto-Detection** - Automatically detects file type and shows compatible output formats
- **Real-Time Progress** - Watch your conversion progress in real-time
- **Dark/Light Mode** - Toggle between dark and light themes
- **Conversion History** - Track your recent conversions (stored locally)
- **Quality Control** - Adjust quality settings for image conversions

## Supported Conversions

### Images
| Input | Output Formats |
|-------|----------------|
| PNG | JPG, WEBP, BMP, GIF |
| JPG/JPEG | PNG, WEBP, BMP, GIF |
| WEBP | PNG, JPG, BMP, GIF |
| BMP | PNG, JPG, WEBP, GIF |
| GIF | PNG, JPG, WEBP, BMP |

### Documents
| Input | Output Formats |
|-------|----------------|
| PDF | TXT, PNG, JPG |

### Data Files
| Input | Output Formats |
|-------|----------------|
| CSV | JSON, XLSX |
| JSON | CSV, XLSX |
| XLSX/XLS | CSV, JSON |

## Quick Start

### Prerequisites

- Python 3.9 or higher
- Node.js 18 or higher
- npm 9 or higher

### Installation

1. **Clone the repository**
   ```bash
   cd fileforge
   ```

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Install frontend dependencies**
   ```bash
   cd frontend
   npm install
   cd ..
   ```

4. **Run the application**
   ```bash
   python run.py
   ```

5. **Open your browser**
   - Frontend: http://localhost:3000
   - API Docs: http://localhost:8000/docs

## Project Structure

```
fileforge/
├── backend/
│   ├── main.py              # FastAPI server
│   ├── utils.py             # Utility functions
│   └── converters/
│       ├── __init__.py
│       ├── image.py         # Image conversions (PIL)
│       ├── document.py      # PDF conversions (pypdf)
│       └── data.py          # Data conversions (pandas)
├── frontend/
│   ├── src/
│   │   ├── App.tsx          # Main application
│   │   ├── main.tsx         # Entry point
│   │   ├── components/
│   │   │   ├── Header.tsx
│   │   │   ├── DropZone.tsx
│   │   │   ├── FileCard.tsx
│   │   │   ├── FormatSelector.tsx
│   │   │   ├── ConvertButton.tsx
│   │   │   ├── ProgressBar.tsx
│   │   │   └── DownloadCard.tsx
│   │   ├── hooks/
│   │   │   └── useFileConvert.ts
│   │   └── styles/
│   │       └── globals.css
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   └── index.html
├── requirements.txt
├── run.py                   # Launcher script
└── README.md
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/upload` | Upload a file |
| POST | `/api/convert` | Convert a file |
| GET | `/api/download/{file_id}` | Download converted file |
| GET | `/api/formats` | Get supported formats |
| GET | `/api/progress/{file_id}` | Get conversion progress |
| GET | `/api/file/{file_id}` | Get file info |
| DELETE | `/api/file/{file_id}` | Delete a file |

## Development

### Running Backend Only
```bash
cd backend
uvicorn main:app --reload --port 8000
```

### Running Frontend Only
```bash
cd frontend
npm run dev
```

### Building for Production

**Frontend:**
```bash
cd frontend
npm run build
```

The built files will be in `frontend/dist/`.

## Tech Stack

### Backend
- **FastAPI** - Modern Python web framework
- **Uvicorn** - ASGI server
- **Pillow** - Image processing
- **pypdf** - PDF manipulation
- **pandas** - Data manipulation
- **openpyxl** - Excel file support

### Frontend
- **React 18** - UI library
- **TypeScript** - Type safety
- **Vite** - Build tool
- **Tailwind CSS** - Styling
- **Framer Motion** - Animations
- **Lucide React** - Icons
- **Axios** - HTTP client
- **React Dropzone** - File uploads

## Configuration

### Environment Variables

**Frontend** (`.env`):
```env
VITE_API_URL=http://localhost:8000
```

### File Size Limits

The default maximum file size is 100MB. This can be configured in `backend/main.py`.

## License

MIT License - feel free to use this project for personal or commercial purposes.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---

Made with ❤️ using FastAPI and React
