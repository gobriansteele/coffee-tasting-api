from typing import Optional
from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class RoasterBase(BaseModel):
    """Base roaster schema with common fields."""
    name: str = Field(..., min_length=1, max_length=255, description="Roaster name")
    location: Optional[str] = Field(None, max_length=255, description="Roaster location")
    website: Optional[str] = Field(None, max_length=500, description="Roaster website URL")
    description: Optional[str] = Field(None, description="Roaster description")
    
    @field_validator('website')
    @classmethod
    def validate_website(cls, v: Optional[str]) -> Optional[str]:
        """Auto-add https:// prefix if missing."""
        if v and not v.startswith(('http://', 'https://')):
            return f"https://{v}"
        return v


class RoasterCreate(RoasterBase):
    """Schema for creating a new roaster."""
    pass


class RoasterUpdate(BaseModel):
    """Schema for updating an existing roaster."""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Roaster name")
    location: Optional[str] = Field(None, max_length=255, description="Roaster location")
    website: Optional[str] = Field(None, max_length=500, description="Roaster website URL")
    description: Optional[str] = Field(None, description="Roaster description")
    
    @field_validator('website')
    @classmethod
    def validate_website(cls, v: Optional[str]) -> Optional[str]:
        """Auto-add https:// prefix if missing."""
        if v and not v.startswith(('http://', 'https://')):
            return f"https://{v}"
        return v


class RoasterResponse(RoasterBase):
    """Schema for roaster responses."""
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RoasterListResponse(BaseModel):
    """Schema for roaster list responses."""
    roasters: list[RoasterResponse]
    total: int
    page: int
    size: int