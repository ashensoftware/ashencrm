from pydantic import BaseModel
from typing import Optional, List


class CatalogCategory(BaseModel):
    name: str
    label: str
    icon: str = ""


class ScrapeRequest(BaseModel):
    category: str
    city: str = "Medellín"
    limit: int = 10
    lat: Optional[float] = None
    lon: Optional[float] = None


class PatchProspectData(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    prompt_used: Optional[str] = None
    demo_url: Optional[str] = None
    whatsapp_message: Optional[str] = None
    lovable_account_used: Optional[str] = None


class RenameCategoryRequest(BaseModel):
    old_name: str
    new_name: str


class PatchCatalogCategory(BaseModel):
    label: Optional[str] = None
    icon: Optional[str] = None


class ResetCategoryAssignmentBody(BaseModel):
    category: str
