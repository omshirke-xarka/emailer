"""
Emails API routes
"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from app.data.emails import emails_service
from app.data.contacts import contacts_service
from app.data.templates import templates_service
from app.services.email_service import email_service
from app.models.email import (
    EmailListResponse, EmailDetailResponse, EmailSendRequest, EmailSendResponse,
    EmailScheduleRequest, EmailScheduleResponse, EmailPreviewRequest, EmailPreviewResponse,
    EmailCancelResponse
)

router = APIRouter()

@router.get("", response_model=EmailListResponse)
async def list_emails():
    """List sent emails with aggregate stats"""
    try:
        emails = await emails_service.list_emails()
        return EmailListResponse(data=emails, total=len(emails), page=1, limit=len(emails))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/scheduled", response_model=EmailListResponse)
async def list_scheduled_emails():
    """List scheduled emails"""
    try:
        emails = await emails_service.list_scheduled_emails()
        return EmailListResponse(data=emails, total=len(emails), page=1, limit=len(emails))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{email_id}", response_model=EmailDetailResponse)
async def get_email_detail(email_id: str):
    """Get email detail with per-recipient tracking"""
    try:
        detail = await emails_service.get_email_detail(email_id)
        if not detail:
            raise HTTPException(status_code=404, detail="Email not found")
        return EmailDetailResponse(**detail)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/send", response_model=EmailSendResponse)
async def send_email(email_request: EmailSendRequest):
    """Send email immediately"""
    try:
        result = await email_service.send_email(email_request.dict())
        return EmailSendResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/preview", response_model=EmailPreviewResponse)
async def preview_email(preview_request: EmailPreviewRequest):
    """Preview email (resolve template with a contact)"""
    try:
        result = await email_service.preview_email(
            preview_request.body_html,
            preview_request.contact_id,
            preview_request.list_id
        )
        return EmailPreviewResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/schedule", response_model=EmailScheduleResponse)
async def schedule_email(schedule_request: EmailScheduleRequest):
    """Schedule email for later"""
    try:
        # Validate scheduled_at is a future date
        from datetime import datetime
        scheduled = datetime.fromisoformat(schedule_request.scheduled_at)
        if scheduled.timestamp() <= datetime.now().timestamp():
            raise HTTPException(status_code=400, detail="scheduledAt must be a valid future date")
        
        result = await email_service.schedule_email(schedule_request.dict())
        return EmailScheduleResponse(**result)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{email_id}/cancel", response_model=EmailCancelResponse)
async def cancel_scheduled_email(email_id: str):
    """Cancel a scheduled email"""
    try:
        await emails_service.cancel_scheduled_email(email_id)
        return EmailCancelResponse(success=True)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))