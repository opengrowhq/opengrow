from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator


class InviteCreate(BaseModel):
    email: EmailStr
    role: str = "member"  # "member" | "admin"

    @field_validator("role")
    @classmethod
    def _valid_role(cls, v: str) -> str:
        v = v.strip().lower()
        if v not in ("member", "admin"):
            raise ValueError("role must be 'member' or 'admin'")
        return v


class InviteOut(BaseModel):
    id: str
    email: str
    role: str
    status: str
    expires_at: datetime


class InviteAcceptRequest(BaseModel):
    display_name: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=8, max_length=200)

    @field_validator("display_name", mode="before")
    @classmethod
    def _strip(cls, value):
        return value.strip() if isinstance(value, str) else value


class MemberOut(BaseModel):
    id: str
    email: str
    display_name: str
