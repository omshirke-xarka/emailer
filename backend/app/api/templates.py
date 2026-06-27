"""
Templates API routes
"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from app.data.templates import templates_service
from app.models.template import (
    Template, TemplateListResponse, TemplateCreateRequest, TemplateUpdateRequest
)

router = APIRouter()

@router.get("/", response_model=TemplateListResponse)
async def list_templates():
    """List all templates"""
    try:
        templates = await templates_service.list_templates()
        return TemplateListResponse(data=templates, total=len(templates))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{template_id}", response_model=Template)
async def get_template(template_id: str):
    """Get single template"""
    try:
        template = await templates_service.get_template(template_id)
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        return template
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/", response_model=Template, status_code=201)
async def create_template(template: TemplateCreateRequest):
    """Create template"""
    try:
        return await templates_service.create_template(template.dict())
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/{template_id}", response_model=Template)
async def update_template(template_id: str, template: TemplateUpdateRequest):
    """Update template"""
    try:
        updated = await templates_service.update_template(template_id, template.dict(exclude_unset=True))
        if not updated:
            raise HTTPException(status_code=404, detail="Template not found")
        return updated
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{template_id}")
async def delete_template(template_id: str):
    """Delete template"""
    try:
        await templates_service.delete_template(template_id)
        return None
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))