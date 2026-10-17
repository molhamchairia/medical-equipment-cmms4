from copy import deepcopy

DEFAULT_SETTINGS = {
    "shifts": {
        "morning": {"start": "07:00", "end": "15:00"},
        "evening": {"start": "15:00", "end": "23:00"},
        "night": {"start": "23:00", "end": "07:00"},
    },
    "sla_table": {
        "P1": {"ack_minutes": 15, "repeat_minutes": 30, "resolution_hours": 24},
        "P2": {"ack_minutes": 120, "repeat_minutes": 240, "resolution_hours": 72},
        "P3": {"ack_minutes": 1440, "repeat_minutes": 1440, "resolution_hours": 168},
        "P4": {"ack_minutes": 4320, "repeat_minutes": None, "resolution_hours": 336},
    },
    "priority_matrix": {
        "very_high": {"stopped": "P1", "degraded": "P1", "cosmetic": "P2"},
        "high": {"stopped": "P1", "degraded": "P2", "cosmetic": "P3"},
        "medium": {"stopped": "P2", "degraded": "P3", "cosmetic": "P4"},
        "low": {"stopped": "P3", "degraded": "P4", "cosmetic": "P4"},
    },
    "missed_check_grace_minutes": 30,
    "pm_lead_days": 7,
    "pm_overdue_grace_days": {"very_high": 7, "high": 14, "medium": 30, "low": 30},
    "notification_poll_seconds": 20,
    "backup_keep_days": 30,
    "pm_default_days": {"very_high": 90, "high": 180, "medium": 365, "low": 365},
}

def defaults():
    return deepcopy(DEFAULT_SETTINGS)
