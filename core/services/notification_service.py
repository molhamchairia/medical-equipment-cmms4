from datetime import datetime
from core.models import Notification

def send(session, recipient_id, type, title, body, priority="normal", entity_type=None, entity_id=None, requires_ack=False):
    item = Notification(recipient_id=recipient_id, type=type, title=title, body=body, priority=priority, entity_type=entity_type, entity_id=entity_id, requires_ack=requires_ack)
    session.add(item)
    return item

def unread_count(session, user_id):
    return session.query(Notification).filter_by(recipient_id=user_id, read_at=None).count()

def mark_read(session, notification, acknowledge=False):
    now = datetime.utcnow()
    notification.read_at = notification.read_at or now
    if acknowledge and notification.requires_ack: notification.acked_at = now
