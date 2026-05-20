"""
Email service with AWS SES integration and template processing
"""
import re
import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid

from app.config import get_settings
from app.data.contacts import contacts_service
from app.data.emails import emails_service
from app.data.templates import templates_service
from app.models.contact import Contact, DynamicContact
from app.models.email import EmailRecord
from app.utils.helpers import (
    resolve_template, 
    detect_email_column, 
    detect_name_column,
    inject_preheader,
    inject_tracking_pixel,
    rewrite_links
)
from app.utils.rate_limiter import wait_for_next_email_send

settings = get_settings()

class EmailService:
    def __init__(self):
        self.settings = settings
    
    async def send_email(self, options: Dict[str, Any]) -> Dict[str, Any]:
        """Send email immediately"""
        contact_ids = options['contact_ids']
        subject = options['subject']
        body_html = options['body_html']
        preview_text = options.get('preview_text')
        template_id = options.get('template_id')
        list_id = options.get('list_id')
        
        # Create email record
        email_record = await emails_service.create_email_record({
            'subject': subject,
            'body_html': body_html,
            'template_id': template_id,
            'sender_email': self.settings.sender_email,
            'contact_ids': contact_ids,
            'list_id': list_id,
        })
        
        sent = 0
        failed = 0
        
        if list_id:
            # Send to contacts from a custom list
            await self._send_to_list_contacts(
                email_record.id, contact_ids, subject, body_html, preview_text, list_id
            )
        else:
            # Send to standard contacts
            await self._send_to_standard_contacts(
                email_record.id, contact_ids, subject, body_html, preview_text
            )
        
        # Update email status
        status = 'sent' if failed == 0 else 'partial' if sent > 0 else 'failed'
        await emails_service.update_email_status(email_record.id, status)
        
        return {
            'sent': sent,
            'failed': failed,
            'email_id': email_record.id
        }
    
    async def schedule_email(self, options: Dict[str, Any]) -> Dict[str, Any]:
        """Schedule email for later"""
        contact_ids = options['contact_ids']
        subject = options['subject']
        body_html = options['body_html']
        preview_text = options.get('preview_text')
        template_id = options.get('template_id')
        scheduled_at = options['scheduled_at']
        list_id = options.get('list_id')
        
        # Create email record with scheduled time
        email_record = await emails_service.create_email_record({
            'subject': subject,
            'body_html': body_html,
            'template_id': template_id,
            'sender_email': self.settings.sender_email,
            'scheduled_at': scheduled_at,
            'contact_ids': contact_ids,
            'preview_text': preview_text,
            'list_id': list_id,
        })
        
        return {
            'email_id': email_record.id,
            'scheduled_at': scheduled_at
        }
    
    async def _send_to_standard_contacts(self, email_id: str, contact_ids: List[int], 
                                       subject: str, body_html: str, preview_text: Optional[str]):
        """Send email to standard contacts"""
        contacts = await contacts_service.get_contacts_by_ids(contact_ids)
        
        for contact in contacts:
            # Wait for rate limit
            await wait_for_next_email_send()
            
            # Resolve template variables
            resolved_subject = subject.replace('{{username}}', contact.username).replace('{{email}}', contact.email)
            resolved_body = body_html.replace('{{username}}', contact.username).replace('{{email}}', contact.email)
            
            if preview_text:
                resolved_preview = preview_text.replace('{{username}}', contact.username).replace('{{email}}', contact.email)
                resolved_body = inject_preheader(resolved_body, resolved_preview)
            
            # Add tracking
            tracking_id = await emails_service.add_recipient(email_id, {
                'contact_id': contact.id,
                'email': contact.email,
                'name': contact.username
            })
            
            resolved_body = rewrite_links(resolved_body, tracking_id)
            resolved_body = inject_tracking_pixel(resolved_body, tracking_id)
            
            # Send via SES
            await self._send_via_ses(contact.email, resolved_subject, resolved_body)
    
    async def _send_to_list_contacts(self, email_id: str, contact_ids: List[int], 
                                   subject: str, body_html: str, preview_text: Optional[str], list_id: str):
        """Send email to contacts from a custom list"""
        list_contacts = await contacts_service.get_contacts_by_ids_for_list(list_id, contact_ids)
        list_meta = await contacts_service.get_contact_list_by_id(list_id)
        
        if not list_contacts or not list_meta:
            return
        
        columns = list_meta.columns
        email_col = detect_email_column(columns)
        name_col = detect_name_column(columns)
        
        for contact in list_contacts:
            # Wait for rate limit
            await wait_for_next_email_send()
            
            # Build template variables
            vars = {}
            for key, value in contact.dict().items():
                if key != 'id':
                    vars[key] = str(value or '')
            
            vars['email'] = str(contact.dict().get(email_col, '') or '')
            if name_col:
                vars['username'] = str(contact.dict().get(name_col, '') or '')
            
            # Resolve template variables
            resolved_subject = resolve_template(subject, vars)
            resolved_body = resolve_template(body_html, vars)
            
            if preview_text:
                resolved_preview = resolve_template(preview_text, vars)
                resolved_body = inject_preheader(resolved_body, resolved_preview)
            
            # Add tracking
            tracking_id = await emails_service.add_recipient(email_id, {
                'contact_id': contact.id,
                'email': vars['email'],
                'name': vars['username']
            })
            
            resolved_body = rewrite_links(resolved_body, tracking_id)
            resolved_body = inject_tracking_pixel(resolved_body, tracking_id)
            
            # Send via SES
            await self._send_via_ses(vars['email'], resolved_subject, resolved_body)
    
    async def _send_via_ses(self, to_email: str, subject: str, body_html: str):
        """Send email via AWS SES"""
        try:
            import boto3
            
            # Create SES client
            ses_client = boto3.client(
                'ses',
                region_name=self.settings.aws_default_region,
                aws_access_key_id=self.settings.aws_access_key_id,
                aws_secret_access_key=self.settings.aws_secret_access_key
            )
            
            # Prepare email
            source = self.settings.aws_ses_from_email
            if not source:
                raise ValueError("AWS_SES_FROM_EMAIL is not set")
            
            # Add sender name if provided
            sender_name = self.settings.ses_sender_name
            source_addr = f"{sender_name} <{source}>" if sender_name else source
            
            # Send email
            ses_client.send_email(
                Source=source_addr,
                Destination={'ToAddresses': [to_email]},
                Message={
                    'Subject': {'Data': subject, 'Charset': 'UTF-8'},
                    'Body': {
                        'Text': {'Data': body_html, 'Charset': 'UTF-8'},
                        'Html': {'Data': body_html, 'Charset': 'UTF-8'}
                    }
                }
            )
            
        except Exception as e:
            # Log error but don't raise to allow other emails to be sent
            print(f"Failed to send email to {to_email}: {str(e)}")
            raise
    
    async def preview_email(self, body_html: str, contact_id: Optional[int] = None, 
                           list_id: Optional[str] = None) -> Dict[str, str]:
        """Preview email with template variables resolved"""
        vars = {'username': 'JohnDoe', 'email': 'john@example.com'}
        
        if list_id and contact_id:
            # Get contact from list
            list_contacts = await contacts_service.get_contacts_by_ids_for_list(list_id, [contact_id])
            if list_contacts:
                contact = list_contacts[0]
                list_meta = await contacts_service.get_contact_list_by_id(list_id)
                columns = list_meta.columns if list_meta else list(contact.dict().keys())
                
                email_col = detect_email_column(columns)
                name_col = detect_name_column(columns)
                
                vars = {}
                for key, value in contact.dict().items():
                    if key != 'id':
                        vars[key] = str(value or '')
                
                vars['email'] = str(contact.dict().get(email_col, '') or '')
                if name_col:
                    vars['username'] = str(contact.dict().get(name_col, '') or '')
        
        elif contact_id:
            # Get standard contact
            contact = await contacts_service.get_contact_by_id(contact_id)
            if contact:
                vars = {'username': contact.username, 'email': contact.email}
        
        # Resolve template
        resolved_html = resolve_template(body_html, vars)
        
        return {'html': resolved_html}

# Global service instance
email_service = EmailService()

# Background task function
async def process_scheduled_emails():
    """Process scheduled emails"""
    is_processing = getattr(process_scheduled_emails, 'is_processing', False)
    if is_processing:
        return
    
    process_scheduled_emails.is_processing = True
    
    try:
        due_emails = await emails_service.get_due_scheduled_emails()
        for email in due_emails:
            try:
                await _send_scheduled_email(email)
            except Exception as e:
                print(f"[Scheduler] Error processing email {email.id}: {str(e)}")
    finally:
        process_scheduled_emails.is_processing = False

async def _send_scheduled_email(email_record: EmailRecord):
    """Send a scheduled email"""
    if not email_record.contact_ids:
        return

    # Reuse send_email logic
    await email_service.send_email({
        'contact_ids': email_record.contact_ids,
        'subject': email_record.subject,
        'body_html': email_record.body_html,
        'preview_text': email_record.preview_text,
        'template_id': email_record.template_id,
        'list_id': email_record.list_id,
    })

    # Mark original record as sent so it won't be picked up again
    await emails_service.update_email_status(email_record.id, 'sent')