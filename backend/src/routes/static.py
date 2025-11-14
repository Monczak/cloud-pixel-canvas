from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from config import config

static_router = APIRouter(prefix="/static")

@static_router.get("/{file_path:path}")
async def serve_static_file(file_path: str):
    if not config.is_local():
        raise HTTPException(status_code=404, detail="Not found")
    
    safe_path = Path(config.local_storage_path) / file_path
    
    try:
        resolved_path = safe_path.resolve()
        storage_base = Path(config.local_storage_path).resolve()
        
        if not str(resolved_path).startswith(str(storage_base)):
            raise HTTPException(status_code=403, detail="Access denied")
        
        if not resolved_path.exists() or not resolved_path.is_file():
            raise HTTPException(status_code=404, detail="File not found")
        
        media_type = "application/octet-stream"
        if resolved_path.suffix.lower() == ".png":
            media_type = "image/png"
        
        return FileResponse(resolved_path, media_type=media_type)
    except Exception as e:
        raise HTTPException(status_code=404, detail="File not found")
