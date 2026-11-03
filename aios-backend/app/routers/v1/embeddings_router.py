from fastapi import APIRouter, Depends

from app.dependencies.auth_dependencies import require_permission
from app.dependencies.service_dependencies import get_embedding_service
from app.schemas.inference import EmbeddingRequest, EmbeddingResponse
from app.security.permissions import Permission
from app.services.embedding_service import EmbeddingService

router = APIRouter(prefix="/embeddings", tags=["Embeddings"])


@router.post("", response_model=EmbeddingResponse)
async def create_embeddings(
    payload: EmbeddingRequest,
    service: EmbeddingService = Depends(get_embedding_service),
    _principal=Depends(require_permission(Permission.EMBEDDING_CREATE)),
):
    vectors = await service.embed_texts(payload.model_id, payload.texts)
    return EmbeddingResponse(model_id=payload.model_id, vectors=vectors)
