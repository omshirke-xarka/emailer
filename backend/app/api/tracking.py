"""
Email tracking API routes
"""
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse, Response
from app.data.emails import emails_service
import base64

# 1x1 transparent PNG
PIXEL_BASE64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
PIXEL_BYTES = base64.b64decode(PIXEL_BASE64)
# no-store keeps image proxies (e.g. Gmail's) from caching the pixel,
# so repeat opens still reach the server
PIXEL_HEADERS = {
    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
    "Pragma": "no-cache",
    "Expires": "0",
}

router = APIRouter()

@router.get("/open/{tracking_id}.png")
async def track_email_open(tracking_id: str, request: Request):
    """Track email open via pixel"""
    try:
        await emails_service.record_open(tracking_id, request.headers.get("user-agent"))
    except Exception as e:
        # Don't fail the pixel request even if tracking fails
        print(f"Failed to record open for {tracking_id}: {str(e)}")

    return Response(content=PIXEL_BYTES, media_type="image/png", headers=PIXEL_HEADERS)

@router.get("/click/{tracking_id}")
async def track_email_click(tracking_id: str, request: Request, url: str = None):
    """Track link click and redirect"""
    try:
        await emails_service.record_click(tracking_id, request.headers.get("user-agent"))
    except Exception as e:
        # Don't fail the click request even if tracking fails
        print(f"Failed to record click for {tracking_id}: {str(e)}")

    # Validate and redirect to the original destination.
    # FastAPI has already URL-decoded `url` once, so it arrives intact
    # (including any &, =, ? in its own query string).
    if url and (url.startswith('https://') or url.startswith('http://')):
        return RedirectResponse(url=url, status_code=302)
    else:
        return RedirectResponse(url="/", status_code=302)