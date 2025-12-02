"""
FileForge Backend - FastAPI Server

This module provides the REST API for the FileForge file conversion service,
handling file uploads, conversions, downloads, and progress tracking.
"""

import asyncio
import logging
import os
import shutil
import tempfile
import threading
import time
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from converters.image import ImageConverter, ImageConversionError
from converters.document import DocumentConverter, DocumentConversionError
from converters.data import DataConverter, DataConversionError
from utils import (
    ConversionProgress,
    FileCategory,
    cleanup_old_files,
    detect_file_type,
    ensure_directory_exists,
    generate_file_id,
    get_all_supported_formats,
    get_compatible_formats,
    get_file_extension_for_format,
    get_safe_filename,
    validate_conversion,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Configuration constants
UPLOAD_DIR = Path(tempfile.gettempdir()) / "fileforge" / "uploads"
OUTPUT_DIR = Path(tempfile.gettempdir()) / "fileforge" / "outputs"
MAX_UPLOAD_SIZE_MB = 100
FILE_EXPIRY_SECONDS = 3600  # 1 hour
CLEANUP_INTERVAL_SECONDS = 300  # 5 minutes

# In-memory storage for file metadata and progress
file_registry: Dict[str, Dict[str, Any]] = {}
progress_registry: Dict[str, ConversionProgress] = {}
registry_lock = threading.Lock()

# Initialize converters
image_converter = ImageConverter()
document_converter = DocumentConverter()
data_converter = DataConverter()


# Pydantic models for API
class ConvertRequest(BaseModel):
    """Request model for file conversion."""
    file_id: str = Field(..., description="ID of the uploaded file")
    output_format: str = Field(..., description="Target format for conversion")
    options: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Conversion options (quality, etc.)"
    )


class UploadResponse(BaseModel):
    """Response model for file upload."""
    file_id: str
    filename: str
    size: int
    format: str
    category: str
    compatible_formats: List[str]
    upload_time: str


class ConvertResponse(BaseModel):
    """Response model for conversion request."""
    file_id: str
    output_file_id: str
    status: str
    message: str


class ProgressResponse(BaseModel):
    """Response model for progress query."""
    file_id: str
    status: str
    progress: int
    message: str
    error: Optional[str] = None
    output_file_id: Optional[str] = None


class FormatInfo(BaseModel):
    """Information about a supported format."""
    outputs: List[str]
    category: str


class FormatsResponse(BaseModel):
    """Response model for formats endpoint."""
    categories: Dict[str, Any]
    conversions: Dict[str, FormatInfo]


def cleanup_task():
    """Background task to clean up expired files."""
    while True:
        try:
            time.sleep(CLEANUP_INTERVAL_SECONDS)

            # Cleanup files
            deleted_uploads = cleanup_old_files(UPLOAD_DIR, FILE_EXPIRY_SECONDS)
            deleted_outputs = cleanup_old_files(OUTPUT_DIR, FILE_EXPIRY_SECONDS)

            if deleted_uploads or deleted_outputs:
                logger.info(
                    f"Cleanup: removed {len(deleted_uploads)} uploads, "
                    f"{len(deleted_outputs)} outputs"
                )

            # Cleanup registry entries
            current_time = time.time()
            with registry_lock:
                expired_ids = []
                for file_id, info in file_registry.items():
                    upload_time = info.get("upload_timestamp", 0)
                    if current_time - upload_time > FILE_EXPIRY_SECONDS:
                        expired_ids.append(file_id)

                for file_id in expired_ids:
                    file_registry.pop(file_id, None)
                    progress_registry.pop(file_id, None)

                if expired_ids:
                    logger.info(f"Cleanup: removed {len(expired_ids)} registry entries")

        except Exception as e:
            logger.error(f"Cleanup task error: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup and shutdown."""
    # Startup
    logger.info("FileForge Backend starting up...")

    # Ensure directories exist
    ensure_directory_exists(UPLOAD_DIR)
    ensure_directory_exists(OUTPUT_DIR)

    # Start cleanup background thread
    cleanup_thread = threading.Thread(target=cleanup_task, daemon=True)
    cleanup_thread.start()

    logger.info(f"Upload directory: {UPLOAD_DIR}")
    logger.info(f"Output directory: {OUTPUT_DIR}")
    logger.info("FileForge Backend ready")

    yield

    # Shutdown
    logger.info("FileForge Backend shutting down...")


# Create FastAPI application
app = FastAPI(
    title="FileForge API",
    description="File conversion service supporting images, documents, and data files",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",  # Vite default
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint returning API information."""
    return {
        "name": "FileForge API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "upload": "POST /api/upload",
            "convert": "POST /api/convert",
            "download": "GET /api/download/{file_id}",
            "formats": "GET /api/formats",
            "progress": "GET /api/progress/{file_id}",
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "upload_dir_exists": UPLOAD_DIR.exists(),
        "output_dir_exists": OUTPUT_DIR.exists(),
    }


@app.post("/api/upload", response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...)):
    """
    Upload a file for conversion.

    Args:
        file: The file to upload.

    Returns:
        Upload response with file ID and metadata.

    Raises:
        HTTPException: If upload fails or file is invalid.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    # Sanitize filename
    safe_filename = get_safe_filename(file.filename)

    # Generate unique file ID
    file_id = generate_file_id()

    # Create file path
    file_path = UPLOAD_DIR / file_id / safe_filename
    ensure_directory_exists(file_path.parent)

    try:
        # Read and validate file size
        content = await file.read()
        file_size = len(content)
        file_size_mb = file_size / (1024 * 1024)

        if file_size_mb > MAX_UPLOAD_SIZE_MB:
            raise HTTPException(
                status_code=413,
                detail=f"File size ({file_size_mb:.1f}MB) exceeds maximum ({MAX_UPLOAD_SIZE_MB}MB)"
            )

        if file_size == 0:
            raise HTTPException(status_code=400, detail="Empty file uploaded")

        # Save file
        with open(file_path, "wb") as f:
            f.write(content)

        # Detect file type
        file_format, category = detect_file_type(file_path)

        if category == FileCategory.UNKNOWN:
            # Clean up and reject
            shutil.rmtree(file_path.parent, ignore_errors=True)
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {file_format}"
            )

        # Get compatible output formats
        compatible_formats = get_compatible_formats(file_format)

        # Store file metadata
        upload_time = datetime.now()
        with registry_lock:
            file_registry[file_id] = {
                "file_id": file_id,
                "filename": safe_filename,
                "original_filename": file.filename,
                "path": str(file_path),
                "size": file_size,
                "format": file_format,
                "category": category.value,
                "compatible_formats": compatible_formats,
                "upload_time": upload_time.isoformat(),
                "upload_timestamp": time.time(),
            }

        logger.info(f"File uploaded: {file_id} ({safe_filename}, {file_size_mb:.2f}MB)")

        return UploadResponse(
            file_id=file_id,
            filename=safe_filename,
            size=file_size,
            format=file_format,
            category=category.value,
            compatible_formats=compatible_formats,
            upload_time=upload_time.isoformat()
        )

    except HTTPException:
        raise
    except Exception as e:
        # Clean up on error
        shutil.rmtree(file_path.parent, ignore_errors=True)
        logger.error(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@app.post("/api/convert", response_model=ConvertResponse)
async def convert_file(request: ConvertRequest):
    """
    Start file conversion.

    Args:
        request: Conversion request with file_id, output_format, and options.

    Returns:
        Conversion response with output file ID.

    Raises:
        HTTPException: If conversion fails or parameters are invalid.
    """
    file_id = request.file_id
    output_format = request.output_format.lower().lstrip(".")
    options = request.options or {}

    # Get file info
    with registry_lock:
        file_info = file_registry.get(file_id)

    if not file_info:
        raise HTTPException(status_code=404, detail="File not found")

    input_path = Path(file_info["path"])
    if not input_path.exists():
        raise HTTPException(status_code=404, detail="File no longer available")

    input_format = file_info["format"]
    category = file_info["category"]

    # Validate conversion
    if not validate_conversion(input_format, output_format):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot convert {input_format} to {output_format}"
        )

    # Generate output file ID
    output_file_id = generate_file_id()

    # Create output path
    output_extension = get_file_extension_for_format(output_format)
    output_filename = f"{input_path.stem}_converted{output_extension}"
    output_path = OUTPUT_DIR / output_file_id / output_filename
    ensure_directory_exists(output_path.parent)

    # Initialize progress tracking
    progress = ConversionProgress(file_id)
    progress.update(status="processing", progress=0, message="Starting conversion")
    with registry_lock:
        progress_registry[file_id] = progress

    # Progress callback
    def update_progress(percent: int, message: str):
        with registry_lock:
            if file_id in progress_registry:
                progress_registry[file_id].update(progress=percent, message=message)

    try:
        # Select converter based on category
        if category == FileCategory.IMAGE.value:
            converter = image_converter
        elif category == FileCategory.DOCUMENT.value:
            converter = document_converter
        elif category == FileCategory.DATA.value:
            converter = data_converter
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file category: {category}"
            )

        # Perform conversion
        result_path = converter.convert(
            input_path=input_path,
            output_path=output_path,
            output_format=output_format,
            options=options,
            progress_callback=update_progress
        )

        # Handle directory output (for PDF to images)
        if result_path.is_dir():
            output_path = result_path

        # Store output file info
        with registry_lock:
            file_registry[output_file_id] = {
                "file_id": output_file_id,
                "filename": output_filename,
                "path": str(result_path),
                "source_file_id": file_id,
                "format": output_format,
                "category": category,
                "is_directory": result_path.is_dir(),
                "upload_time": datetime.now().isoformat(),
                "upload_timestamp": time.time(),
            }

            # Update progress
            progress_registry[file_id].update(
                status="completed",
                progress=100,
                message="Conversion complete",
                output_file_id=output_file_id
            )

        logger.info(f"Conversion complete: {file_id} -> {output_file_id}")

        return ConvertResponse(
            file_id=file_id,
            output_file_id=output_file_id,
            status="completed",
            message="Conversion successful"
        )

    except (ImageConversionError, DocumentConversionError, DataConversionError) as e:
        # Update progress with error
        with registry_lock:
            if file_id in progress_registry:
                progress_registry[file_id].update(
                    status="failed",
                    progress=0,
                    message="Conversion failed",
                    error=str(e)
                )

        logger.error(f"Conversion failed for {file_id}: {e}")
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        # Update progress with error
        with registry_lock:
            if file_id in progress_registry:
                progress_registry[file_id].update(
                    status="failed",
                    progress=0,
                    message="Conversion failed",
                    error=str(e)
                )

        logger.error(f"Conversion error for {file_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Conversion failed: {str(e)}")


@app.get("/api/download/{file_id}")
async def download_file(file_id: str):
    """
    Download a converted file.

    Args:
        file_id: ID of the file to download.

    Returns:
        FileResponse with the file content.

    Raises:
        HTTPException: If file not found.
    """
    # Get file info
    with registry_lock:
        file_info = file_registry.get(file_id)

    if not file_info:
        raise HTTPException(status_code=404, detail="File not found")

    file_path = Path(file_info["path"])

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File no longer available")

    # Handle directory output (create zip for multiple files)
    if file_path.is_dir():
        # Create a zip file of the directory
        zip_path = file_path.with_suffix(".zip")
        if not zip_path.exists():
            shutil.make_archive(str(file_path), "zip", file_path)

        return FileResponse(
            path=zip_path,
            filename=f"{file_info['filename']}.zip",
            media_type="application/zip"
        )

    # Single file download
    filename = file_info.get("filename", file_path.name)

    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/octet-stream"
    )


@app.get("/api/progress/{file_id}", response_model=ProgressResponse)
async def get_progress(file_id: str):
    """
    Get conversion progress for a file.

    Args:
        file_id: ID of the file being converted.

    Returns:
        Progress information.

    Raises:
        HTTPException: If file not found.
    """
    with registry_lock:
        progress = progress_registry.get(file_id)

    if not progress:
        # Check if file exists but no conversion started
        with registry_lock:
            file_info = file_registry.get(file_id)

        if file_info:
            return ProgressResponse(
                file_id=file_id,
                status="pending",
                progress=0,
                message="No conversion in progress"
            )

        raise HTTPException(status_code=404, detail="File not found")

    return ProgressResponse(
        file_id=progress.file_id,
        status=progress.status,
        progress=progress.progress,
        message=progress.message,
        error=progress.error,
        output_file_id=progress.output_file_id
    )


@app.get("/api/formats", response_model=FormatsResponse)
async def get_formats():
    """
    Get all supported file formats and conversions.

    Returns:
        Dictionary of supported formats and conversion mappings.
    """
    formats = get_all_supported_formats()
    return FormatsResponse(**formats)


@app.get("/api/file/{file_id}")
async def get_file_info(file_id: str):
    """
    Get information about an uploaded file.

    Args:
        file_id: ID of the file.

    Returns:
        File information.

    Raises:
        HTTPException: If file not found.
    """
    with registry_lock:
        file_info = file_registry.get(file_id)

    if not file_info:
        raise HTTPException(status_code=404, detail="File not found")

    # Remove internal fields
    response = {k: v for k, v in file_info.items() if k not in ["path", "upload_timestamp"]}

    return response


@app.delete("/api/file/{file_id}")
async def delete_file(file_id: str):
    """
    Delete an uploaded or converted file.

    Args:
        file_id: ID of the file to delete.

    Returns:
        Deletion confirmation.

    Raises:
        HTTPException: If file not found.
    """
    with registry_lock:
        file_info = file_registry.get(file_id)

    if not file_info:
        raise HTTPException(status_code=404, detail="File not found")

    file_path = Path(file_info["path"])

    try:
        if file_path.exists():
            if file_path.is_dir():
                shutil.rmtree(file_path)
            else:
                # Delete parent directory (which contains only this file)
                shutil.rmtree(file_path.parent, ignore_errors=True)

        # Remove from registry
        with registry_lock:
            file_registry.pop(file_id, None)
            progress_registry.pop(file_id, None)

        logger.info(f"File deleted: {file_id}")

        return {"status": "deleted", "file_id": file_id}

    except Exception as e:
        logger.error(f"Delete failed for {file_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")


@app.get("/api/stats")
async def get_stats():
    """
    Get server statistics.

    Returns:
        Server statistics including file counts and storage usage.
    """
    with registry_lock:
        total_files = len(file_registry)
        active_conversions = sum(
            1 for p in progress_registry.values()
            if p.status == "processing"
        )

    # Calculate storage usage
    upload_size = sum(
        f.stat().st_size for f in UPLOAD_DIR.rglob("*") if f.is_file()
    ) if UPLOAD_DIR.exists() else 0

    output_size = sum(
        f.stat().st_size for f in OUTPUT_DIR.rglob("*") if f.is_file()
    ) if OUTPUT_DIR.exists() else 0

    return {
        "total_files": total_files,
        "active_conversions": active_conversions,
        "storage": {
            "uploads_mb": upload_size / (1024 * 1024),
            "outputs_mb": output_size / (1024 * 1024),
            "total_mb": (upload_size + output_size) / (1024 * 1024),
        },
        "config": {
            "max_upload_size_mb": MAX_UPLOAD_SIZE_MB,
            "file_expiry_seconds": FILE_EXPIRY_SECONDS,
        },
        "timestamp": datetime.now().isoformat(),
    }


# Run with: uvicorn main:app --reload --port 8000
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
