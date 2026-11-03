from datetime import datetime

from pydantic import BaseModel


class AuditLogRead(BaseModel):
    id: str
    organization_id: str
    actor: str
    action: str
    resource: str
    ip_address: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}
