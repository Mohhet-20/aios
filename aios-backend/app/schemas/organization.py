from pydantic import BaseModel, Field

from app.schemas.common import TimestampedRead


class OrganizationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    plan: str = "starter"


class OrganizationRead(TimestampedRead):
    name: str
    plan: str
    logo_initials: str


class MembershipCreate(BaseModel):
    user_id: str
    role: str = "member"


class TeamCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class TeamRead(TimestampedRead):
    organization_id: str
    name: str
