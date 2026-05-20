"""
Contacts API routes
"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from app.data.contacts import contacts_service
from app.models.contact import (
    Contact, ContactList, ContactListResponse, ContactListDynamicResponse,
    ContactFilterValues, ContactUploadResponse
)

# Contact Lists endpoints

class ContactListCreate(BaseModel):
    name: str = Field(..., min_length=1, description="Contact list name")
    csv: str = Field(..., min_length=1, description="CSV content for contacts")

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

@router.post("/upload-csv", response_model=ContactUploadResponse)
async def upload_csv(csv: str):
    """Upload CSV to replace contacts"""
    try:
        result = await contacts_service.upload_csv(csv)
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
async def upload_csv_to_list(list_id: str, csv: str):
    """Upload CSV to an existing contact list"""
    try:
        result = await contacts_service.upload_csv_to_list(list_id, csv)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/lists/{list_id}")
async def delete_contact_list(list_id: str):
    """Delete a contact list"""
    try:
        await contacts_service.delete_contact_list(list_id)
        return {"ok": True}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))