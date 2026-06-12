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
            failure_count=0,
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
            send_status=data.get('send_status', 'pending'),
            error_message=data.get('error_message'),
            failure_count=data.get('failure_count', 0),
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

    async def update_recipient_send_status(
        self,
        tracking_id: str,
        send_status: str,
        error_message: Optional[str] = None
    ) -> None:
        """Update recipient delivery status for retry visibility."""
        redis_client = await self._get_redis_client()

        recipient_json = await redis_client.get(self._tracking_key(tracking_id))
        if not recipient_json:
            return

        recipient = RecipientTracking(**json.loads(recipient_json))
        recipient.send_status = send_status
        recipient.error_message = error_message
        if send_status == "sent":
            recipient.sent_at = datetime.now().isoformat()
        if send_status == "failed":
            recipient.failure_count += 1
        await redis_client.set(self._tracking_key(tracking_id), recipient.json())

    async def update_email_send_result(self, email_id: str, sent: int, failed: int) -> None:
        """Update aggregate email delivery status after a send or retry attempt."""
        redis_client = await self._get_redis_client()

        email = await self.get_email_record(email_id)
        if not email:
            return

        if sent > 0 and failed == 0:
            email.status = 'sent'
        elif sent > 0 or email.status == 'partial' or email.total_recipients > failed:
            email.status = 'partial'
        else:
            email.status = 'failed'

        email.failure_count += failed
        email.sent_at = datetime.now().isoformat()
        await redis_client.set(self._email_key(email_id), email.json())

        if email.status != 'scheduled':
            await redis_client.zrem(SCHEDULED_KEY, email_id)
    
    def _classify_hit(self, recipient: RecipientTracking, user_agent: Optional[str]):
        """Detect automated scanner/prefetch hits that should not count as engagement.

        Mail providers (Gmail, Outlook/Defender, corporate gateways) fetch pixels
        and links right after delivery to scan for spam/malware. Real humans never
        engage within seconds of the send, so hits inside the grace window are
        discarded, as are known scanner user agents.

        Returns (ignored_reason, seconds_after_send); reason is None for real hits.
        """
        from app.config import get_settings
        grace_seconds = get_settings().open_tracking_grace_seconds

        elapsed = None
        if recipient.sent_at:
            try:
                elapsed = (datetime.now() - datetime.fromisoformat(recipient.sent_at)).total_seconds()
            except ValueError:
                pass

        if elapsed is not None and grace_seconds > 0 and 0 <= elapsed < grace_seconds:
            return "scanner-prefetch", elapsed

        # GoogleImageProxy is NOT listed: all real Gmail opens come through it
        bot_markers = (
            'bot', 'spider', 'crawler', 'preview', 'scanner', 'scanning',
            'barracuda', 'mimecast', 'proofpoint', 'urldefense', 'safelinks',
            'symantec', 'trendmicro', 'cloudmark', 'headlesschrome', 'python-requests', 'curl/'
        )
        ua = (user_agent or '').lower()
        if any(marker in ua for marker in bot_markers):
            return "bot-user-agent", elapsed

        return None, elapsed

    async def _log_hit(self, redis_client, kind: str, recipient: RecipientTracking,
                       user_agent: Optional[str], ignored_reason: Optional[str],
                       elapsed: Optional[float]) -> None:
        """Keep a capped log of every tracking hit for debugging."""
        entry = {
            "ts": datetime.now().isoformat(),
            "kind": kind,
            "email": recipient.email,
            "tracking_id": recipient.tracking_id,
            "user_agent": user_agent,
            "seconds_after_send": round(elapsed, 1) if elapsed is not None else None,
            "ignored_reason": ignored_reason,
        }
        await redis_client.lpush("tracking:hits", json.dumps(entry))
        await redis_client.ltrim("tracking:hits", 0, 199)

    async def _screen_hit(self, redis_client, kind: str, recipient: RecipientTracking,
                          user_agent: Optional[str]) -> bool:
        """Log the hit and return True if it should be ignored."""
        reason, elapsed = self._classify_hit(recipient, user_agent)
        await self._log_hit(redis_client, kind, recipient, user_agent, reason, elapsed)
        if reason:
            print(f"Ignoring {kind} for {recipient.email}: {reason} ({elapsed}s after send), UA={user_agent}")
            return True
        return False

    async def record_open(self, tracking_id: str, user_agent: Optional[str] = None) -> None:
        """Record email open"""
        redis_client = await self._get_redis_client()

        recipient_json = await redis_client.get(self._tracking_key(tracking_id))
        if not recipient_json:
            return

        recipient = RecipientTracking(**json.loads(recipient_json))

        if await self._screen_hit(redis_client, "open", recipient, user_agent):
            return

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
    
    async def record_click(self, tracking_id: str, user_agent: Optional[str] = None) -> None:
        """Record email click"""
        redis_client = await self._get_redis_client()

        recipient_json = await redis_client.get(self._tracking_key(tracking_id))
        if not recipient_json:
            return

        recipient = RecipientTracking(**json.loads(recipient_json))

        if await self._screen_hit(redis_client, "click", recipient, user_agent):
            return

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
                        'send_status': recipient_data.get('sendStatus', 'sent'),
                        'error_message': recipient_data.get('errorMessage'),
                        'failure_count': recipient_data.get('failureCount', 0),
                        'opened_at': recipient_data.get('opened_at'),
                        'open_count': recipient_data.get('open_count', 0),
                        'clicked_at': recipient_data.get('clicked_at'),
                        'click_count': recipient_data.get('click_count', 0)
                    }
                if 'send_status' not in recipient_data:
                    recipient_data['send_status'] = 'failed' if email.status == 'failed' else 'sent' if email.status == 'sent' else 'pending'
                if 'error_message' not in recipient_data:
                    recipient_data['error_message'] = None
                if 'failure_count' not in recipient_data:
                    recipient_data['failure_count'] = 1 if recipient_data.get('send_status') == 'failed' else 0
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
