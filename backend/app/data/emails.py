"""
Emails data service with Redis integration
"""
import json
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid

from app.data.redis_client import get_redis_client
from app.models.email import EmailRecord, RecipientTracking

EMAILS_KEY = "emails:list"
SCHEDULED_KEY = "emails:scheduled"

class EmailsService:
    def __init__(self):
        self.redis_client = None
    
    async def _get_redis_client(self):
        """Get Redis client instance"""
        if self.redis_client is None:
            self.redis_client = await get_redis_client()
        return self.redis_client
    
    def _email_key(self, email_id: str) -> str:
        """Get email key"""
        return f"email:{email_id}"
    
    def _recipients_key(self, email_id: str) -> str:
        """Get recipients key"""
        return f"email:{email_id}:recipients"
    
    def _tracking_key(self, tracking_id: str) -> str:
        """Get tracking key"""
        return f"tracking:{tracking_id}"
    
    async def create_email_record(self, data: Dict[str, Any]) -> EmailRecord:
        """Create a new email record"""
        redis_client = await self._get_redis_client()
        
        now = datetime.now().isoformat()
        is_scheduled = data.get('scheduled_at') is not None
        
        email_record = EmailRecord(
            id=str(uuid.uuid4()),
            subject=data['subject'],
            body_html=data['body_html'],
            template_id=data.get('template_id'),
            sender_email=data['sender_email'],
            status='scheduled' if is_scheduled else 'sent',
            total_recipients=0,
            total_opens=0,
            total_clicks=0,
            sent_at='' if is_scheduled else now,
            created_at=now,
            scheduled_at=data.get('scheduled_at'),
            contact_ids=data.get('contact_ids'),
            preview_text=data.get('preview_text'),
            list_id=data.get('list_id')
        )
        
        # Save email record
        await redis_client.set(self._email_key(email_record.id), email_record.json())
        
        # Add to emails list
        await redis_client.zadd(EMAILS_KEY, {email_record.id: datetime.now().timestamp()})
        
        # Add to scheduled list if applicable
        if is_scheduled:
            # Store in milliseconds to match the TypeScript server's Date.now() queries
            scheduled_time = datetime.fromisoformat(data['scheduled_at']).timestamp() * 1000
            await redis_client.zadd(SCHEDULED_KEY, {email_record.id: scheduled_time})
        
        return email_record
    
    async def add_recipient(self, email_id: str, data: Dict[str, Any]) -> str:
        """Add a recipient to an email"""
        redis_client = await self._get_redis_client()
        
        tracking_id = str(uuid.uuid4())
        recipient = RecipientTracking(
            tracking_id=tracking_id,
            contact_id=data['contact_id'],
            email_id=email_id,
            email=data['email'],
            name=data['name'],
            opened_at=None,
            open_count=0,
            clicked_at=None,
            click_count=0
        )
        
        # Save recipient tracking
        await redis_client.set(self._tracking_key(tracking_id), recipient.json())
        
        # Add to recipients list
        await redis_client.zadd(self._recipients_key(email_id), {tracking_id: datetime.now().timestamp()})
        
        # Increment total recipients on email record
        email = await self.get_email_record(email_id)
        if email:
            email.total_recipients += 1
            await redis_client.set(self._email_key(email_id), email.json())
        
        return tracking_id
    
    async def record_open(self, tracking_id: str) -> None:
        """Record email open"""
        redis_client = await self._get_redis_client()
        
        recipient_json = await redis_client.get(self._tracking_key(tracking_id))
        if not recipient_json:
            return
        
        recipient = RecipientTracking(**json.loads(recipient_json))
        
        # Update recipient
        is_first_open = recipient.opened_at is None
        recipient.open_count += 1
        if is_first_open:
            recipient.opened_at = datetime.now().isoformat()
        
        await redis_client.set(self._tracking_key(tracking_id), recipient.json())
        
        # Update email record if it's the first open
        if is_first_open:
            email = await self.get_email_record(recipient.email_id)
            if email:
                email.total_opens += 1
                await redis_client.set(self._email_key(recipient.email_id), email.json())
    
    async def record_click(self, tracking_id: str) -> None:
        """Record email click"""
        redis_client = await self._get_redis_client()
        
        recipient_json = await redis_client.get(self._tracking_key(tracking_id))
        if not recipient_json:
            return
        
        recipient = RecipientTracking(**json.loads(recipient_json))
        
        # Update recipient
        is_first_click = recipient.clicked_at is None
        recipient.click_count += 1
        if is_first_click:
            recipient.clicked_at = datetime.now().isoformat()
        
        await redis_client.set(self._tracking_key(tracking_id), recipient.json())
        
        # Update email record if it's the first click
        if is_first_click:
            email = await self.get_email_record(recipient.email_id)
            if email:
                email.total_clicks += 1
                await redis_client.set(self._email_key(recipient.email_id), email.json())
    
    async def update_email_status(self, email_id: str, status: str) -> None:
        """Update email status"""
        redis_client = await self._get_redis_client()
        
        email = await self.get_email_record(email_id)
        if email:
            email.status = status
            await redis_client.set(self._email_key(email_id), email.json())
            
            # Remove from scheduled set if no longer scheduled
            if status != 'scheduled':
                await redis_client.zrem(SCHEDULED_KEY, email_id)
    
    async def list_emails(self) -> List[EmailRecord]:
        """List all emails"""
        redis_client = await self._get_redis_client()
        
        email_ids = await redis_client.zrange(EMAILS_KEY, 0, -1)
        if not email_ids:
            return []
        
        email_ids = [e.decode('utf-8') if isinstance(e, bytes) else e for e in email_ids]
        
        email_keys = [self._email_key(email_id) for email_id in email_ids]
        emails_json = await redis_client.mget(*email_keys)
        
        emails = []
        for email_json in emails_json:
            if email_json:
                emails.append(EmailRecord(**json.loads(email_json)))

        # Sort by created_at descending so newest emails always appear first
        emails.sort(key=lambda e: e.created_at or '', reverse=True)
        return emails
    
    async def get_email_detail(self, email_id: str) -> Optional[Dict[str, Any]]:
        """Get email detail with recipients"""
        redis_client = await self._get_redis_client()
        
        email_json = await redis_client.get(self._email_key(email_id))
        if not email_json:
            return None
        
        email = EmailRecord(**json.loads(email_json))
        
        # Get recipients
        tracking_ids = await redis_client.zrange(self._recipients_key(email_id), 0, -1)
        recipients = []
        
        # Decode tracking IDs from bytes to strings
        tracking_ids = [tracking_id.decode('utf-8') for tracking_id in tracking_ids]
        
        for tracking_id in tracking_ids:
            recipient_json = await redis_client.get(self._tracking_key(tracking_id))
            if recipient_json:
                recipient_data = json.loads(recipient_json)
                # Convert field names from camelCase to snake_case if needed
                if 'trackingId' in recipient_data and 'tracking_id' not in recipient_data:
                    recipient_data = {
                        'tracking_id': recipient_data.get('trackingId'),
                        'contact_id': recipient_data.get('contactId'),
                        'email_id': recipient_data.get('emailId'),
                        'email': recipient_data.get('email'),
                        'name': recipient_data.get('name'),
                        'opened_at': recipient_data.get('opened_at'),
                        'open_count': recipient_data.get('open_count', 0),
                        'clicked_at': recipient_data.get('clicked_at'),
                        'click_count': recipient_data.get('click_count', 0)
                    }
                recipients.append(RecipientTracking(**recipient_data))
        
        return {"email": email, "recipients": recipients}
    
    async def get_due_scheduled_emails(self) -> List[EmailRecord]:
        """Get scheduled emails that are due"""
        redis_client = await self._get_redis_client()
        
        current_time = datetime.now().timestamp() * 1000  # scores stored in ms
        email_ids = await redis_client.zrange(SCHEDULED_KEY, 0, current_time, by_score=True)
        
        if not email_ids:
            return []

        email_ids = [e.decode('utf-8') if isinstance(e, bytes) else e for e in email_ids]
        email_keys = [self._email_key(email_id) for email_id in email_ids]
        emails_json = await redis_client.mget(*email_keys)

        emails = []
        for email_json in emails_json:
            if email_json:
                email = EmailRecord(**json.loads(email_json))
                if email.status == 'scheduled':
                    emails.append(email)

        return emails

    async def list_scheduled_emails(self) -> List[EmailRecord]:
        """List all scheduled emails"""
        redis_client = await self._get_redis_client()

        email_ids = await redis_client.zrange(SCHEDULED_KEY, 0, -1)
        if not email_ids:
            return []

        email_ids = [e.decode('utf-8') if isinstance(e, bytes) else e for e in email_ids]
        email_keys = [self._email_key(email_id) for email_id in email_ids]
        emails_json = await redis_client.mget(*email_keys)
        
        emails = []
        for email_json in emails_json:
            if email_json:
                email = EmailRecord(**json.loads(email_json))
                if email.status == 'scheduled':
                    emails.append(email)
        
        return emails
    
    async def cancel_scheduled_email(self, email_id: str) -> None:
        """Cancel a scheduled email"""
        redis_client = await self._get_redis_client()
        
        email = await self.get_email_record(email_id)
        if not email:
            raise ValueError("Email not found")
        if email.status != 'scheduled':
            raise ValueError("Email is not scheduled")
        
        email.status = 'cancelled'
        await redis_client.set(self._email_key(email_id), email.json())
        await redis_client.zrem(SCHEDULED_KEY, email_id)
    
    async def get_email_record(self, email_id: str) -> Optional[EmailRecord]:
        """Get email record by ID"""
        redis_client = await self._get_redis_client()
        
        email_json = await redis_client.get(self._email_key(email_id))
        if not email_json:
            return None
        
        return EmailRecord(**json.loads(email_json))

# Global service instance
emails_service = EmailsService()