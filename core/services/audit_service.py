from core.models import AuditLog

def log(session, entity_type, entity_id, action, user_id=None, old_value=None, new_value=None):
    session.add(AuditLog(entity_type=entity_type, entity_id=entity_id, action=action, user_id=user_id, old_value=old_value, new_value=new_value))
