from datetime import datetime, timedelta
import bcrypt
from core.models import User, AuditLog

LOCKOUT_MINUTES = 5
MAX_FAILED_LOGINS = 5

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(password: str, password_hash: str) -> bool:
    try: return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, TypeError): return False

def authenticate(session, username: str, password: str):
    user = session.query(User).filter_by(username=username).one_or_none()
    now = datetime.utcnow()
    if not user or not user.is_active:
        session.add(AuditLog(entity_type="user", entity_id=user.id if user else None, action="login_failed", new_value={"username": username}, user_id=user.id if user else None))
        session.commit(); return None
    if user.locked_until and user.locked_until > now:
        return None
    if not verify_password(password, user.password_hash):
        user.failed_login_count += 1
        if user.failed_login_count >= MAX_FAILED_LOGINS:
            user.locked_until = now + timedelta(minutes=LOCKOUT_MINUTES)
            user.failed_login_count = 0
        session.add(AuditLog(entity_type="user", entity_id=user.id, action="login_failed", user_id=user.id))
        session.commit(); return None
    user.failed_login_count = 0; user.locked_until = None; user.last_login_at = now
    session.add(AuditLog(entity_type="user", entity_id=user.id, action="login", user_id=user.id))
    session.commit()
    return user

def change_password(session, user: User, new_password: str):
    if len(new_password) < 10: raise ValueError("Password must be at least 10 characters")
    user.password_hash = hash_password(new_password)
    user.must_change_password = False
    session.add(AuditLog(entity_type="user", entity_id=user.id, action="password_changed", user_id=user.id))
    session.commit()
