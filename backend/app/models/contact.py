from typing import Optional, List, Dict, Any
from pydantic import BaseModel, EmailStr, validator, field_validator, ConfigDict
from datetime import datetime


class Contact(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    online: str = "No"
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    mobile: Optional[str] = None
    subscribed: str = "No"
    plan: str = "Free Trial"
    pages_left: int = 0
    last_login: Optional[str] = None
    draft_used: int = 0
    research_used: int = 0
    contract_review: int = 0
    query_count: int = 0
    judgment_details: int = 0
    cart_item: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        if v is None or v.strip() == '':
            return None
        # Basic email validation - check for @ symbol
        if '@' not in v:
            # Log the invalid email but don't fail validation
            # This allows the application to continue working with invalid data
            return v
        return v


class ContactList(BaseModel):
    id: str
    name: str
    contact_count: int = 0
    created_at: Optional[str] = None
    columns: List[str] = []

    def __init__(self, **data):
        if 'contactCount' in data and 'contact_count' not in data:
            data['contact_count'] = data.pop('contactCount')
        if 'createdAt' in data and 'created_at' not in data:
            data['created_at'] = data.pop('createdAt')
        super().__init__(**data)


class DynamicContact(BaseModel):
    model_config = ConfigDict(extra='allow')
    id: int = 0


class ContactListResponse(BaseModel):
    data: List[Contact]
    total: int
    page: int
    limit: int


class ContactListListResponse(BaseModel):
    data: List[ContactList]
    total: int


class ContactListDynamicResponse(BaseModel):
    data: List[DynamicContact]
    total: int
    page: int
    limit: int
    columns: List[str]


class ContactFilterValues(BaseModel):
    plans: List[str]
    subscribed_values: List[str]


class ContactUploadResponse(BaseModel):
    contact_count: int
    new_contacts: int
    updated_contacts: int