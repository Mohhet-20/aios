"""SearchService — federated search across prompts, agents, and documents
within a workspace. A naive substring match today (no dedicated search
index); the interface (`search(workspace_id, query) -> categorized
results`) is what a future full-text/vector-hybrid search implementation
would preserve, so callers (the Global Search UI) never need to change.
"""

from __future__ import annotations

from app.repositories.agent_repository import AgentRepository
from app.repositories.knowledge_repository import DocumentRepository
from app.repositories.prompt_repository import PromptRepository


class SearchService:
    def __init__(self, prompts: PromptRepository, agents: AgentRepository, documents: DocumentRepository):
        self.prompts = prompts
        self.agents = agents
        self.documents = documents

    async def search(self, workspace_id: str, query: str) -> dict[str, list]:
        query_lower = query.lower()

        prompts = await self.prompts.list(workspace_id=workspace_id)
        agents = await self.agents.list(workspace_id=workspace_id)
        documents = await self.documents.list(workspace_id=workspace_id)

        return {
            "prompts": [
                p for p in prompts if query_lower in p.name.lower() or query_lower in p.description.lower()
            ],
            "agents": [
                a for a in agents if query_lower in a.name.lower() or query_lower in a.description.lower()
            ],
            "documents": [d for d in documents if query_lower in d.name.lower()],
        }
