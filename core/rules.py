from datetime import datetime, date, time, timedelta
from zoneinfo import ZoneInfo
from core.config import DEFAULT_SETTINGS

ALLOWED_STATUS_TRANSITIONS = {
    "operational": {"reported_faulty", "under_maintenance", "out_of_service"},
    "reported_faulty": {"operational", "under_maintenance", "out_of_service"},
    "under_maintenance": {"operational", "out_of_service"},
    "out_of_service": {"under_maintenance", "decommissioned"},
    "decommissioned": set(),
}
SEVERITY_RANK = {"cosmetic": 1, "degraded": 2, "stopped": 3}

def priority_for(risk_class: str, severity: str, matrix=None) -> str:
    matrix = matrix or DEFAULT_SETTINGS["priority_matrix"]
    return matrix[risk_class][severity]

def validate_transition(old: str, new: str) -> None:
    if new == old: return
    if new not in ALLOWED_STATUS_TRANSITIONS.get(old, set()):
        raise ValueError(f"Invalid device status transition: {old} -> {new}")

def inspection_policy(risk_class: str, override: str | None = None) -> str:
    if override: return override
    return {"very_high": "per_shift", "high": "daily", "medium": "none", "low": "none"}[risk_class]

def current_window(now: datetime, policy: str = "per_shift", shifts=None):
    """Return (shift_name, start, end) in Damascus local naive datetimes."""
    tz = ZoneInfo("Asia/Damascus")
    if now.tzinfo is None: now = now.replace(tzinfo=tz)
    else: now = now.astimezone(tz)
    local = now.replace(tzinfo=None)
    shifts = shifts or DEFAULT_SETTINGS["shifts"]
    if policy == "daily":
        start_time = time.fromisoformat(shifts["morning"]["start"])
        start = datetime.combine(local.date(), start_time)
        if local < start: start -= timedelta(days=1)
        return "day", start, start + timedelta(days=1)
    for name, cfg in shifts.items():
        st, en = time.fromisoformat(cfg["start"]), time.fromisoformat(cfg["end"])
        start = datetime.combine(local.date(), st)
        end = datetime.combine(local.date(), en)
        if en <= st: end += timedelta(days=1)
        if local < start and en <= st: start -= timedelta(days=1); end -= timedelta(days=1)
        if start <= local < end: return name, start, end
    # Handles unusual configurable gaps with a predictable next-window fallback.
    return "day", datetime.combine(local.date(), time.min), datetime.combine(local.date() + timedelta(days=1), time.min)

def work_order_number(year: int, sequence: int) -> str:
    return f"WO-{year:04d}-{sequence:06d}"

def procurement_number(year: int, sequence: int) -> str:
    return f"PR-{year:04d}-{sequence:06d}"
