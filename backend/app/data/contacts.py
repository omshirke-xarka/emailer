"""
Contacts data service with Redis integration
"""
import json
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid

from app.data.redis_client import get_redis_client
from app.models.contact import Contact, ContactList, DynamicContact
from app.utils.helpers import (
    csv_to_contacts, 
    csv_to_dynamic_contacts, 
    detect_email_column, 
    detect_name_column,
    parse_csv_lines
)

CONTACTS_KEY = "contacts:all"
CONTACT_LISTS_KEY = "contactlists:index"

class ContactsService:
    def __init__(self):
        self.redis_client = None
    
    async def _get_redis_client(self):
        """Get Redis client instance"""
        if self.redis_client is None:
            self.redis_client = await get_redis_client()
        return self.redis_client
    
    async def ensure_loaded(self):
        """Ensure contacts are loaded from Redis"""
        redis_client = await self._get_redis_client()
        
        # Check if contacts exist in Redis
        cached_contacts = await redis_client.get(CONTACTS_KEY)
        if cached_contacts:
            # Clean up invalid contacts if they exist
            await self._cleanup_invalid_contacts()
            return
        
        await redis_client.set(CONTACTS_KEY, json.dumps([]))
    
    async def upload_csv(self, csv_content: str) -> Dict[str, int]:
        """Upload CSV to replace contacts"""
        incoming_contacts = csv_to_contacts(csv_content)
        if not incoming_contacts:
            raise ValueError("CSV contains no valid contacts")
        
        await self.ensure_loaded()
        redis_client = await self._get_redis_client()
        
        # Get existing contacts
        existing_contacts_json = await redis_client.get(CONTACTS_KEY)
        existing_contacts = []
        if existing_contacts_json:
            existing_contacts = [Contact(**contact) for contact in json.loads(existing_contacts_json)]
        
        # Build map of existing contacts by email
        existing_by_email = {contact.email.lower(): contact for contact in existing_contacts}
        
        # Merge contacts
        merged_contacts = []
        new_count = 0
        updated_count = 0
        next_id = max([c.id for c in existing_contacts], default=0) + 1
        
        for contact in incoming_contacts:
            email_key = contact.email.lower()
            if email_key in existing_by_email:
                # Update existing contact
                merged_contact = contact.copy(update={'id': existing_by_email[email_key].id})
                merged_contacts.append(merged_contact)
                updated_count += 1
            else:
                # Add new contact
                merged_contacts.append(contact)
                new_count += 1
        
        # Save to Redis
        await redis_client.set(CONTACTS_KEY, json.dumps([c.dict() for c in merged_contacts]))
        
        return {
            "contact_count": len(merged_contacts),
            "new_contacts": new_count,
            "updated_contacts": updated_count
        }
    
    async def get_contacts(self) -> List[Contact]:
        """Get all contacts"""
        try:
            await self.ensure_loaded()
            redis_client = await self._get_redis_client()
            
            contacts_json = await redis_client.get(CONTACTS_KEY)
            if not contacts_json:
                return []
            
            contacts_data = json.loads(contacts_json)
            valid_contacts = []
            invalid_count = 0
            
            for contact_data in contacts_data:
                try:
                    contact = Contact(**contact_data)
                    valid_contacts.append(contact)
                except Exception as e:
                    print(f"Skipping invalid contact: {e}")
                    invalid_count += 1
                    continue
            
            if invalid_count > 0:
                print(f"Found {invalid_count} invalid contacts that were skipped")
            
            return valid_contacts
        except Exception as e:
            print(f"Error getting contacts: {e}")
            return []
    
    async def get_contact_by_id(self, contact_id: int) -> Optional[Contact]:
        """Get contact by ID"""
        contacts = await self.get_contacts()
        return next((c for c in contacts if c.id == contact_id), None)
    
    async def get_contacts_by_ids(self, contact_ids: List[int]) -> List[Contact]:
        """Get contacts by IDs"""
        contacts = await self.get_contacts()
        id_set = set(contact_ids)
        return [c for c in contacts if c.id in id_set]
    
    async def search_contacts(self, search: str = None, subscribed: str = None,
                            plan: str = None, page: int = 1, limit: int = 50) -> Dict[str, Any]:
        """Search contacts with filtering and pagination"""
        try:
            contacts = await self.get_contacts()
            
            # Apply filters
            filtered_contacts = contacts
            
            if search:
                search_lower = search.lower()
                filtered_contacts = [
                    c for c in filtered_contacts
                    if search_lower in c.username.lower() or (c.email and search_lower in c.email.lower())
                ]
            
            if subscribed:
                filtered_contacts = [c for c in filtered_contacts if c.subscribed == subscribed]
            
            if plan:
                filtered_contacts = [c for c in filtered_contacts if c.plan == plan]
            
            # Apply pagination
            total = len(filtered_contacts)
            if limit == 0:
                return {"data": filtered_contacts, "total": total, "page": 1, "limit": total}
            
            offset = (page - 1) * limit
            paginated_contacts = filtered_contacts[offset:offset + limit]
            
            return {
                "data": paginated_contacts,
                "total": total,
                "page": page,
                "limit": limit
            }
        except Exception as e:
            print(f"Error searching contacts: {e}")
            return {"data": [], "total": 0, "page": 1, "limit": limit}
    
    async def get_filter_values(self) -> Dict[str, List[str]]:
        """Get distinct filter values for dropdowns"""
        contacts = await self.get_contacts()
        plans = list(set(c.plan for c in contacts))
        subscribed_values = list(set(c.subscribed for c in contacts))
        return {"plans": sorted(plans), "subscribed_values": sorted(subscribed_values)}
    
    # Contact Lists methods
    async def get_contact_lists(self) -> List[ContactList]:
        """Get all contact lists"""
        try:
            redis_client = await self._get_redis_client()
            lists_json = await redis_client.get(CONTACT_LISTS_KEY)

            if not lists_json:
                return []

            valid_lists = []
            for list_data in json.loads(lists_json):
                try:
                    valid_lists.append(ContactList(**list_data))
                except Exception as e:
                    print(f"Skipping invalid contact list: {e}")

            return valid_lists
        except Exception as e:
            print(f"Error getting contact lists: {e}")
            return []

    async def get_contact_list_by_id(self, list_id: str) -> Optional[ContactList]:
        """Get contact list by ID"""
        lists = await self.get_contact_lists()
        return next((l for l in lists if l.id == list_id), None)
    
    async def create_contact_list(self, name: str, csv_content: str) -> ContactList:
        """Create a new contact list from CSV"""
        print(f"DEBUG: Creating contact list '{name}' with CSV content")
        columns, contacts = csv_to_dynamic_contacts(csv_content)
        print(f"DEBUG: Got {len(contacts)} contacts from CSV")
        if not contacts:
            raise ValueError("CSV contains no valid contacts")
        
        redis_client = await self._get_redis_client()
        
        # Generate unique ID
        list_id = str(uuid.uuid4())
        
        # Create list metadata
        contact_list = ContactList(
            id=list_id,
            name=name,
            contact_count=len(contacts),
            created_at=datetime.now().isoformat(),
            columns=columns
        )
        
        # Get existing lists
        existing_lists_json = await redis_client.get(CONTACT_LISTS_KEY)
        existing_lists = []
        if existing_lists_json:
            existing_lists = [ContactList(**list_data) for list_data in json.loads(existing_lists_json)]
        
        # Add new list
        existing_lists.append(contact_list)
        await redis_client.set(CONTACT_LISTS_KEY, json.dumps([l.dict() for l in existing_lists]))
        
        # Save contacts for this list
        await redis_client.set(f"contacts:list:{list_id}", json.dumps([c.dict() for c in contacts]))
        
        return contact_list
    
    async def get_contacts_by_ids_for_list(self, list_id: str, contact_ids: List[int]) -> List[DynamicContact]:
        """Get specific contacts from a list by their IDs"""
        all_contacts = await self.get_contacts_for_list(list_id)
        id_set = set(contact_ids)
        return [c for c in all_contacts if c.id in id_set]

    async def get_contacts_for_list(self, list_id: str) -> List[DynamicContact]:
        """Get contacts for a specific list"""
        redis_client = await self._get_redis_client()

        if list_id == "all":
            await self.ensure_loaded()

        key = CONTACTS_KEY if list_id == "all" else f"contacts:list:{list_id}"
        contacts_json = await redis_client.get(key)
        if not contacts_json:
            return []

        return [DynamicContact(**contact_data) for contact_data in json.loads(contacts_json)]
    
    async def search_contacts_for_list(self, list_id: str, search: str = None, 
                                    page: int = 1, limit: int = 50) -> Dict[str, Any]:
        """Search contacts within a specific list"""
        all_contacts = await self.get_contacts_for_list(list_id)
        
        # Apply search filter
        if search:
            search_lower = search.lower()
            filtered_contacts = [
                c for c in all_contacts
                if any(search_lower in str(v).lower() for v in c.dict().values() if v is not None)
            ]
        else:
            filtered_contacts = all_contacts
        
        # Apply pagination
        total = len(filtered_contacts)
        if limit == 0:
            return {"data": filtered_contacts, "total": total, "page": 1, "limit": total}
        
        offset = (page - 1) * limit
        paginated_contacts = filtered_contacts[offset:offset + limit]
        
        return {
            "data": paginated_contacts,
            "total": total,
            "page": page,
            "limit": limit
        }
    
    async def upload_csv_to_list(self, list_id: str, csv_content: str) -> Dict[str, Any]:
        """Upload CSV to an existing contact list"""
        columns, incoming_contacts = csv_to_dynamic_contacts(csv_content)
        if not incoming_contacts:
            raise ValueError("CSV contains no valid contacts")
        
        redis_client = await self._get_redis_client()
        
        # Get existing contacts for this list
        existing_contacts_json = await redis_client.get(f"contacts:list:{list_id}")
        existing_contacts = []
        if existing_contacts_json:
            existing_contacts = [DynamicContact(**contact_data) for contact_data in json.loads(existing_contacts_json)]
        
        # Find email column for deduplication
        email_col = detect_email_column(columns)
        
        # Build map of existing contacts by email
        existing_by_email = {}
        for i, contact in enumerate(existing_contacts):
            email_val = str(contact.dict().get(email_col, '') or '').lower()
            if email_val:
                existing_by_email[email_val] = i
        
        # Merge contacts
        merged_contacts = []
        new_count = 0
        updated_count = 0
        next_id = max([c.id for c in existing_contacts], default=0) + 1
        
        for contact in incoming_contacts:
            contact_dict = contact.dict()
            email_val = str(contact_dict.get(email_col, '') or '').lower()
            
            if email_val in existing_by_email:
                # Update existing contact
                existing_idx = existing_by_email[email_val]
                merged_contact = contact.copy(update={'id': existing_contacts[existing_idx].id})
                merged_contacts.append(merged_contact)
                updated_count += 1
            else:
                # Add new contact
                merged_contacts.append(contact)
                new_count += 1
        
        # Save updated contacts
        await redis_client.set(f"contacts:list:{list_id}", json.dumps([c.dict() for c in merged_contacts]))
        
        # Update list metadata
        lists = await self.get_contact_lists()
        list_entry = next((l for l in lists if l.id == list_id), None)
        if list_entry:
            list_entry.contact_count = len(merged_contacts)
            list_entry.columns = columns
            
            # Save updated lists
            await redis_client.set(CONTACT_LISTS_KEY, json.dumps([l.dict() for l in lists]))
        
        return {
            "contact_count": len(merged_contacts),
            "new_contacts": new_count,
            "updated_contacts": updated_count,
            "columns": columns
        }
    
    async def delete_contact_list(self, list_id: str) -> None:
        """Delete a contact list"""
        redis_client = await self._get_redis_client()
        
        # Get existing lists
        existing_lists_json = await redis_client.get(CONTACT_LISTS_KEY)
        existing_lists = []
        if existing_lists_json:
            existing_lists = [ContactList(**list_data) for list_data in json.loads(existing_lists_json)]
        
        # Remove list
        filtered_lists = [l for l in existing_lists if l.id != list_id]
        if len(filtered_lists) == len(existing_lists):
            raise ValueError("Contact list not found")
        
        # Save updated lists
        await redis_client.set(CONTACT_LISTS_KEY, json.dumps([l.dict() for l in filtered_lists]))
        
        # Delete contacts for this list
        await redis_client.delete(f"contacts:list:{list_id}")
    
    async def _cleanup_invalid_contacts(self):
        """Clean up contacts with invalid email addresses"""
        try:
            redis_client = await self._get_redis_client()
            contacts_json = await redis_client.get(CONTACTS_KEY)
            
            if not contacts_json:
                return
            
            contacts_data = json.loads(contacts_json)
            valid_contacts = []
            invalid_count = 0
            
            for contact_data in contacts_data:
                try:
                    # Check if email is valid (contains @ symbol)
                    email = contact_data.get('email', '')
                    if email and '@' not in email:
                        print(f"Removing invalid contact: {contact_data.get('username', 'unknown')} with email: {email}")
                        invalid_count += 1
                        continue
                    
                    contact = Contact(**contact_data)
                    valid_contacts.append(contact)
                except Exception as e:
                    print(f"Removing invalid contact due to validation error: {e}")
                    invalid_count += 1
                    continue
            
            if invalid_count > 0:
                print(f"Cleaned up {invalid_count} invalid contacts")
                await redis_client.set(CONTACTS_KEY, json.dumps([c.dict() for c in valid_contacts]))
                
                # Update contact lists count
                lists = await self.get_contact_lists()
                for contact_list in lists:
                    if contact_list.id == "list1":  # Default contacts list
                        contact_list.contact_count = len(valid_contacts)
                        break
                
                await redis_client.set(CONTACT_LISTS_KEY, json.dumps([l.dict() for l in lists]))
        except Exception as e:
            print(f"Error cleaning up invalid contacts: {e}")

# Global service instance
contacts_service = ContactsService()
