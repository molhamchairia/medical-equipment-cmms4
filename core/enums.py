from enum import StrEnum

class Role(StrEnum):
    NURSE = "nurse"
    ENGINEER = "engineer"
    SUPERVISOR = "supervisor"
    PROCUREMENT = "procurement"

class DeviceStatus(StrEnum):
    OPERATIONAL = "operational"
    REPORTED_FAULTY = "reported_faulty"
    UNDER_MAINTENANCE = "under_maintenance"
    OUT_OF_SERVICE = "out_of_service"
    DECOMMISSIONED = "decommissioned"

class RiskClass(StrEnum):
    VERY_HIGH = "very_high"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class Priority(StrEnum):
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"
    P4 = "P4"

class Severity(StrEnum):
    STOPPED = "stopped"
    DEGRADED = "degraded"
    COSMETIC = "cosmetic"

class WorkOrderStatus(StrEnum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    IN_PROGRESS = "in_progress"
    WAITING_PARTS = "waiting_parts"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
