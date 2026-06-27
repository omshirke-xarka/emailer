"""
Email tracking API routes
"""
from fastapi import APIRouter, HTTPException, Request
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
        # Record click in background
        import asyncio
        asyncio.create_task(emails_service.record_click(tracking_id))
        
        # Validate and redirect URL
        if url and (url.startswith('https://') or url.startswith('http://')):
            # In a real implementation, you'd return a redirect response
            # For now, return the URL that should be redirected to
            return {"redirect_url": url}
        else:
            # Return home page URL
            return {"redirect_url": "/"}
    except Exception as e:
        # Don't fail the click request even if tracking fails
        return {"redirect_url": "/"}