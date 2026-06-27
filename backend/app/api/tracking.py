"""
Email tracking API routes
"""
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from app.data.emails import emails_service
import base64

# 1x1 transparent PNG
PIXEL_BASE64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="

router = APIRouter()

@router.get("/open/{tracking_id}.png")
async def track_email_open(tracking_id: str, request: Request):
    """Track email open via pixel"""
    try:
        # Record open in background
        import asyncio
        asyncio.create_task(emails_service.record_open(tracking_id))
        
        # Return pixel image
        return {
            "content": base64.b64decode(PIXEL_BASE64),
            "media_type": "image/png"
        }
    except Exception as e:
        # Don't fail the pixel request even if tracking fails
        return {
            "content": base64.b64decode(PIXEL_BASE64),
            "media_type": "image/png"
        }

@router.get("/click/{tracking_id}")
async def track_email_click(tracking_id: str, url: str = None):
    """Track link click and redirect"""
    try:
        import asyncio
        asyncio.create_task(emails_service.record_click(tracking_id))
        
        if url and (url.startswith('https://') or url.startswith('http://')):
            return RedirectResponse(url=url, status_code=302)
        else:
        return RedirectResponse(url="/", status_code=302)

    except Exception as e:
        return RedirectResponse(url="/", status_code=302)