from typing import Literal, Optional, List
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime


class EmailRecord(BaseModel):
    id: str
    subject: str
    body_html: str
    template_id: Optional[str] = None
    sender_email: EmailStr
    status: str = "sent"  # 'sent' | 'partial' | 'failed' | 'scheduled' | 'cancelled'
    total_recipients: int = 0
    total_opens: int = 0
    total_clicks: int = 0
    failure_count: int = 0
    sent_at: Optional[str] = None
    created_at: Optional[str] = None
    scheduled_at: Optional[str] = None
    contact_ids: Optional[List[int]] = None
    preview_text: Optional[str] = None
    list_id: Optional[str] = None


class RecipientTracking(BaseModel):
    tracking_id: str
    contact_id: int
    email_id: str
    email: EmailStr
    name: str
    send_status: str = "pending"
    sent_at: Optional[str] = None
    error_message: Optional[str] = None
    failure_count: int = 0
    opened_at: Optional[str] = None
    open_count: int = 0
    clicked_at: Optional[str] = None
    click_count: int = 0


class EmailListResponse(BaseModel):
    data: List[EmailRecord]
    total: int
    page: int
    limit: int


class EmailDetailResponse(BaseModel):
    email: EmailRecord
    recipients: List[RecipientTracking]


class EmailSendRequest(BaseModel):
    contact_ids: List[int] = Field(default=None, validation_alias='contactIds')
    subject: str
    body_html: str = Field(default=None, validation_alias='bodyHtml')
    preview_text: Optional[str] = Field(default=None, validation_alias='previewText')
    template_id: Optional[str] = Field(default=None, validation_alias='templateId')
    list_id: Optional[str] = Field(default=None, validation_alias='listId')
    
    # Also accept snake_case
    class Config:
        populate_by_name = True


class EmailSendResponse(BaseModel):
    sent: int
    failed: int
    email_id: str


class EmailScheduleRequest(EmailSendRequest):
    scheduled_at: str = Field(default=None, validation_alias='scheduledAt')


class EmailScheduleResponse(BaseModel):
    email_id: str
    scheduled_at: str


class EmailPreviewRequest(BaseModel):
    body_html: str
    contact_id: Optional[int] = None
    list_id: Optional[str] = None


class EmailPreviewResponse(BaseModel):
    html: str


class EmailCancelResponse(BaseModel):
    success: bool


class EmailProviderRequest(BaseModel):
    provider: Literal["aws", "resend"]


class EmailProviderResponse(BaseModel):
    provider: Literal["aws", "resend"]
