"""Aggregate-specific repository ports beyond generic CRUD. Only defined
where a service genuinely needs a query the generic base can't express
(e.g. "find user by email", "find the production version of a prompt").
Everything else is satisfied by `AbstractRepository`'s generic methods.
"""

from __future__ import annotations

from abc import abstractmethod
from typing import Protocol

from app.domain.entities.agent import Agent
from app.domain.entities.identity import Organization, User
from app.domain.entities.prompt import Prompt
from app.domain.repositories.base import AbstractRepository


class UserRepository(AbstractRepository[User], Protocol):
    @abstractmethod
    async def get_by_email(self, email: str) -> User | None: ...


class OrganizationRepository(AbstractRepository[Organization], Protocol):
    @abstractmethod
    async def get_by_name(self, name: str) -> Organization | None: ...


class PromptRepository(AbstractRepository[Prompt], Protocol):
    @abstractmethod
    async def get_production_version(self, prompt_id: str) -> Prompt | None: ...


class AgentRepository(AbstractRepository[Agent], Protocol):
    @abstractmethod
    async def list_by_workspace(self, workspace_id: str) -> list[Agent]: ...
