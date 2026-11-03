from fastapi import APIRouter, Depends, Query

from app.dependencies.service_dependencies import get_search_service
from app.schemas.search import SearchResults
from app.services.search_service import SearchService

router = APIRouter(prefix="/search", tags=["Search"])


@router.get("", response_model=SearchResults)
async def search(
    workspace_id: str, q: str = Query(min_length=1), service: SearchService = Depends(get_search_service)
):
    results = await service.search(workspace_id, q)
    return SearchResults(
        prompts=[{"id": p.id, "name": p.name} for p in results["prompts"]],
        agents=[{"id": a.id, "name": a.name} for a in results["agents"]],
        documents=[{"id": d.id, "name": d.name} for d in results["documents"]],
    )
