"""Identity aggregates: User, Organization, Team. Membership (user <-> org,
user <-> team) is modeled as its own small value object rather than nested
collections, since membership carries its own attribute (role) and needs to
be queried independently (e.g. "list all members of org X").
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from app.domain.value_objects.enums import PlanTier
from app.security.permissions import Role


@dataclass
class User:
    id: str
    email: str
    full_name: str
    hashed_password: str
    is_active: bool = True
    is_superuser: bool = False
    created_at: datetime | None = None

    def verify_active(self) -> None:
        from app.domain.exceptions import AuthenticationError

        if not self.is_active:
            raise AuthenticationError("This user account has been deactivated")


@dataclass
class OrganizationMembership:
    user_id: str
    organization_id: str
    role: Role


@dataclass
class Organization:
    id: str
    name: str
    plan: PlanTier = PlanTier.STARTER
    members: list[OrganizationMembership] = field(default_factory=list)

    def role_of(self, user_id: str) -> Role | None:
        membership = next((m for m in self.members if m.user_id == user_id), None)
        return membership.role if membership else None


@dataclass
class Team:
    id: str
    organization_id: str
    name: str
    member_user_ids: list[str] = field(default_factory=list)
