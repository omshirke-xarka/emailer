"""
Contacts API routes
"""
from typing import Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, EmailStr, Field
from app.data.contacts import contacts_service
from app.models.contact import (
    Contact, ContactList, ContactListResponse, ContactListDynamicResponse,
    ContactFilterValues, ContactUploadResponse, DynamicContact
)

# Contact Lists endpoints

class ContactListCreate(BaseModel):
    name: str = Field(..., min_length=1, description="Contact list name")
    csv: str = Field(..., min_length=1, description="CSV content for contacts")

class CsvUploadRequest(BaseModel):
    csv: str = Field(..., min_length=1, description="CSV content for contacts")

class ContactCreate(BaseModel):
    username: str = Field(..., min_length=1, description="Contact username")
    email: EmailStr = Field(..., description="Contact email")
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    mobile: Optional[str] = None
    subscribed: str = "No"
    plan: str = "Free Trial"

class ListContactCreate(BaseModel):
    fields: Dict[str, str] = Field(..., description="Column values for the new contact")

router = APIRouter()

@router.get("", response_model=ContactListResponse)
async def list_contacts(
    search: Optional[str] = Query(None, description="Search by username or email"),
    subscribed: Optional[str] = Query(None, description="Filter by subscription status"),
    plan: Optional[str] = Query(None, description="Filter by plan"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=0, le=1000, description="Items per page")
):
    """List contacts with filtering and pagination"""
    try:
        result = await contacts_service.search_contacts(
            search=search, subscribed=subscribed, plan=plan, page=page, limit=limit
        )
        return ContactListResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/filters", response_model=ContactFilterValues)
async def get_contact_filters():
    """Get distinct filter values for dropdowns"""
    try:
        return await contacts_service.get_filter_values()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("", response_model=Contact)
async def create_contact(request: ContactCreate):
    """Create a single contact manually"""
    try:
        return await contacts_service.add_contact(request.dict())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upload-csv", response_model=ContactUploadResponse)
async def upload_csv(request: CsvUploadRequest):
    """Upload CSV to replace contacts"""
    try:
        result = await contacts_service.upload_csv(request.csv)
        return ContactUploadResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Contact Lists endpoints

@router.get("/lists", response_model=List[ContactList])
async def get_contact_lists():
    """Get all contact lists"""
    try:
        return await contacts_service.get_contact_lists()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/lists", response_model=ContactList)
async def create_contact_list(request: ContactListCreate):
    """Create a new contact list from CSV"""
    try:
        return await contacts_service.create_contact_list(request.name, request.csv)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/lists/{list_id}", response_model=ContactListDynamicResponse)
async def get_contacts_for_list(
    list_id: str,
    search: Optional[str] = Query(None, description="Search contacts"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=0, le=1000, description="Items per page")
):
    """Get contacts for a specific list"""
    try:
        if list_id == "all":
            result = await contacts_service.search_contacts_for_list(
                list_id, search=search, page=page, limit=limit
            )
            return ContactListDynamicResponse(
                data=result["data"],
                total=result["total"],
                page=result["page"],
                limit=result["limit"],
                columns=list(Contact.model_fields.keys())
            )

        # Get list metadata to include columns
        list_meta = await contacts_service.get_contact_list_by_id(list_id)
        if not list_meta:
            raise HTTPException(status_code=404, detail="Contact list not found")
        
        result = await contacts_service.search_contacts_for_list(
            list_id, search=search, page=page, limit=limit
        )
        
        return ContactListDynamicResponse(
            data=result["data"],
            total=result["total"],
            page=result["page"],
            limit=result["limit"],
            columns=list_meta.columns
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/lists/{list_id}/upload-csv")
async def upload_csv_to_list(list_id: str, request: CsvUploadRequest):
    """Upload CSV to an existing contact list"""
    try:
        if list_id == "all":
            result = await contacts_service.upload_csv(request.csv)
            return ContactUploadResponse(**result)

        result = await contacts_service.upload_csv_to_list(list_id, request.csv)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/lists/{list_id}/contacts", response_model=DynamicContact)
async def add_contact_to_list(list_id: str, request: ListContactCreate):
    """Add a single contact to a custom list manually"""
    try:
        if list_id == "all":
            raise HTTPException(status_code=400, detail="Use POST /api/contacts to add to All Contacts")
        return await contacts_service.add_contact_to_list(list_id, request.fields)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/lists/{list_id}")
async def delete_contact_list(list_id: str):
    """Delete a contact list"""
    try:
        if list_id == "all":
            raise HTTPException(status_code=400, detail="All Contacts cannot be deleted")

        await contacts_service.delete_contact_list(list_id)
        return {"ok": True}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
