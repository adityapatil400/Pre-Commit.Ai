from typing import Dict, List
from fastapi import APIRouter, File, HTTPException, UploadFile
from backend.app.services.file_service import FileService, FileServiceError
from backend.app.utils.logger import logger

router = APIRouter(prefix="/upload", tags=["Upload"])

@router.post("/file", summary="Upload and extract a Python file or ZIP archive")
async def upload_file_endpoint(file: UploadFile = File(...)):
    """
    Accepts a single Python file (.py) or a compressed project archive (.zip).
    Validates file boundaries (Zip-Slip prevention) and returns the extracted manifest.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename missing from upload.")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        if file.filename.endswith(".zip"):
            extracted = FileService.extract_zip_archive(content)
        elif file.filename.endswith(".py"):
            extracted = FileService.extract_single_python_file(file.filename, content)
        else:
            raise HTTPException(
                status_code=400,
                detail="Unsupported file format. Please upload a .py file or .zip archive."
            )
    except FileServiceError as e:
        logger.error(f"Upload extraction error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "filename": file.filename,
        "files_count": len(extracted),
        "manifest": list(extracted.keys()),
        "total_lines": sum(len(c.splitlines()) for c in extracted.values()),
    }

