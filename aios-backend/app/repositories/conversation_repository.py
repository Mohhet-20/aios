from sqlalchemy import select

from app.models.conversation import ConversationMessageModel, ConversationModel
from app.repositories.base import SQLAlchemyRepository


class ConversationRepository(SQLAlchemyRepository[ConversationModel]):
    model = ConversationModel


class ConversationMessageRepository(SQLAlchemyRepository[ConversationMessageModel]):
    model = ConversationMessageModel

    async def list_for_conversation(self, conversation_id: str) -> list[ConversationMessageModel]:
        result = await self.session.execute(
            select(ConversationMessageModel)
            .where(ConversationMessageModel.conversation_id == conversation_id)
            .order_by(ConversationMessageModel.created_at.asc())
        )
        return list(result.scalars().all())
