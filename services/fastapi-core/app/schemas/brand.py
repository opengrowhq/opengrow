from datetime import datetime

from pydantic import BaseModel


class BrandCreate(BaseModel):
    name: str
    source_url: str | None = None  # if set, kicks off Brand DNA extraction


class BrandUpdate(BaseModel):
    name: str | None = None
    profile: dict | None = None  # user refinements to the extracted profile


class BrandOut(BaseModel):
    id: str
    name: str
    source_url: str | None = None
    status: str
    profile: dict | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime
