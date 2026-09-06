from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class Me(BaseModel):
    id: str
    email: EmailStr
    display_name: str
    tenant_id: str
    tenant_slug: str
