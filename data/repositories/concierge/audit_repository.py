from data.models.concierge.audit_log import AuditLog
from data.repositories.base_repository import BaseRepository


class AuditRepository(BaseRepository[AuditLog]):
    model = AuditLog
    business_id_field = "audit_id"
