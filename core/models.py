from datetime import datetime, timezone
from sqlalchemy import String, Integer, Boolean, DateTime, Date, Text, ForeignKey, Numeric, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from core.db import Base

def utcnow(): return datetime.now(timezone.utc).replace(tzinfo=None)

class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

class Department(TimestampMixin, Base):
    __tablename__ = "departments"
    id: Mapped[int] = mapped_column(primary_key=True)
    name_ar: Mapped[str] = mapped_column(String(120), unique=True)
    name_en: Mapped[str | None] = mapped_column(String(120))
    code: Mapped[str] = mapped_column(String(12), unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

class User(TimestampMixin, Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(160))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), index=True)
    department_id: Mapped[int | None] = mapped_column(ForeignKey("departments.id"), index=True)
    phone: Mapped[str | None] = mapped_column(String(40))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime)
    failed_login_count: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime)
    department = relationship("Department")

class EngineerDepartment(Base):
    __tablename__ = "engineer_departments"
    engineer_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id", ondelete="CASCADE"), primary_key=True)

class DeviceCategory(TimestampMixin, Base):
    __tablename__ = "device_categories"
    id: Mapped[int] = mapped_column(primary_key=True)
    name_ar: Mapped[str] = mapped_column(String(140))
    name_en: Mapped[str] = mapped_column(String(140))
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("device_categories.id"))
    default_risk_class: Mapped[str] = mapped_column(String(20), default="medium")
    default_pm_interval_days: Mapped[int | None] = mapped_column(Integer)
    gmdn_code: Mapped[str | None] = mapped_column(String(40))

class Device(TimestampMixin, Base):
    __tablename__ = "devices"
    id: Mapped[int] = mapped_column(primary_key=True)
    asset_tag: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(180), index=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("device_categories.id"), index=True)
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"), index=True)
    room_location: Mapped[str | None] = mapped_column(String(120))
    manufacturer: Mapped[str | None] = mapped_column(String(120))
    model: Mapped[str | None] = mapped_column(String(120))
    serial_number: Mapped[str | None] = mapped_column(String(120), index=True)
    risk_class: Mapped[str] = mapped_column(String(20), default="medium")
    status: Mapped[str] = mapped_column(String(30), default="operational", index=True)
    inspection_policy_override: Mapped[str | None] = mapped_column(String(20))
    pm_interval_days: Mapped[int | None] = mapped_column(Integer)
    pm_interval_source: Mapped[str] = mapped_column(String(20), default="standard")
    acquisition_date: Mapped[datetime | None] = mapped_column(Date)
    acquisition_source: Mapped[str] = mapped_column(String(20), default="unknown")
    donor_name: Mapped[str | None] = mapped_column(String(160))
    warranty_expiry: Mapped[datetime | None] = mapped_column(Date)
    qr_code_value: Mapped[str | None] = mapped_column(String(40))
    notes: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    category = relationship("DeviceCategory")
    department = relationship("Department")

class MaintenanceSchedule(TimestampMixin, Base):
    __tablename__ = "maintenance_schedules"
    id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), index=True)
    type: Mapped[str] = mapped_column(String(30), default="preventive")
    interval_days: Mapped[int] = mapped_column(Integer)
    interval_source: Mapped[str] = mapped_column(String(20), default="standard")
    last_done_at: Mapped[datetime | None] = mapped_column(DateTime)
    next_due_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

class MaintenanceRecord(TimestampMixin, Base):
    __tablename__ = "maintenance_records"
    __table_args__ = (Index("ix_wo_status_priority", "status", "priority"), Index("ix_wo_device_status", "device_id", "status"))
    id: Mapped[int] = mapped_column(primary_key=True)
    wo_number: Mapped[str] = mapped_column(String(24), unique=True, index=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), index=True)
    type: Mapped[str] = mapped_column(String(30), default="corrective")
    origin: Mapped[str] = mapped_column(String(30), default="nurse_fault")
    schedule_id: Mapped[int | None] = mapped_column(ForeignKey("maintenance_schedules.id"))
    nursing_check_id: Mapped[int | None] = mapped_column(Integer)
    priority: Mapped[str] = mapped_column(String(5), index=True)
    severity: Mapped[str | None] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(30), default="open", index=True)
    reported_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    assigned_engineer_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    symptom_text: Mapped[str | None] = mapped_column(Text)
    photo_path: Mapped[str | None] = mapped_column(String(255))
    reported_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)
    escalation_level: Mapped[int] = mapped_column(Integer, default=0)
    fault_cause_code: Mapped[str | None] = mapped_column(String(40))
    action_taken: Mapped[str | None] = mapped_column(Text)
    parts_used: Mapped[str | None] = mapped_column(Text)
    labor_minutes: Mapped[int | None] = mapped_column(Integer)
    verified_functional: Mapped[bool] = mapped_column(Boolean, default=False)
    completion_note: Mapped[str | None] = mapped_column(Text)
    device = relationship("Device")
    reporter = relationship("User", foreign_keys=[reported_by])
    assigned_engineer = relationship("User", foreign_keys=[assigned_engineer_id])

class StatusReport(Base):
    __tablename__ = "status_reports"
    id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), index=True)
    status: Mapped[str] = mapped_column(String(30))
    previous_status: Mapped[str | None] = mapped_column(String(30))
    source: Mapped[str] = mapped_column(String(30))
    reported_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    maintenance_record_id: Mapped[int | None] = mapped_column(ForeignKey("maintenance_records.id"))
    nursing_check_id: Mapped[int | None] = mapped_column(Integer)
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

class NursingCheck(TimestampMixin, Base):
    __tablename__ = "nursing_checks"
    id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), index=True)
    nurse_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"))
    shift: Mapped[str] = mapped_column(String(20))
    window_start: Mapped[datetime] = mapped_column(DateTime)
    window_end: Mapped[datetime] = mapped_column(DateTime)
    submitted_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    overall_result: Mapped[str] = mapped_column(String(20))
    bulk_ok: Mapped[bool] = mapped_column(Boolean, default=False)
    template_id: Mapped[int | None] = mapped_column(Integer)
    template_version: Mapped[int] = mapped_column(Integer, default=1)

class ChecklistTemplate(TimestampMixin, Base):
    __tablename__ = "checklist_templates"
    id: Mapped[int] = mapped_column(primary_key=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("device_categories.id"), index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

class ChecklistItem(Base):
    __tablename__ = "checklist_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    template_id: Mapped[int] = mapped_column(ForeignKey("checklist_templates.id", ondelete="CASCADE"), index=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    text_ar: Mapped[str] = mapped_column(String(240))
    fail_severity: Mapped[str] = mapped_column(String(20))
    is_required: Mapped[bool] = mapped_column(Boolean, default=True)

class NursingCheckResult(Base):
    __tablename__ = "nursing_check_results"
    id: Mapped[int] = mapped_column(primary_key=True)
    check_id: Mapped[int] = mapped_column(ForeignKey("nursing_checks.id", ondelete="CASCADE"), index=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("checklist_items.id"))
    result: Mapped[str] = mapped_column(String(20))
    note: Mapped[str | None] = mapped_column(Text)

class ProcurementRequest(TimestampMixin, Base):
    __tablename__ = "procurement_requests"
    id: Mapped[int] = mapped_column(primary_key=True)
    pr_number: Mapped[str] = mapped_column(String(24), unique=True, index=True)
    maintenance_record_id: Mapped[int | None] = mapped_column(ForeignKey("maintenance_records.id"))
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), index=True)
    requested_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    item_description: Mapped[str] = mapped_column(Text)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    urgency: Mapped[str] = mapped_column(String(5), default="P3")
    estimated_cost: Mapped[float | None] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    supplier: Mapped[str | None] = mapped_column(String(160))
    status: Mapped[str] = mapped_column(String(20), default="requested", index=True)
    handled_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    ordered_at: Mapped[datetime | None] = mapped_column(DateTime)
    expected_delivery_date: Mapped[datetime | None] = mapped_column(Date)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime)
    note: Mapped[str | None] = mapped_column(Text)
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=False)

class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (Index("ix_notification_recipient_read", "recipient_id", "read_at"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    recipient_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    type: Mapped[str] = mapped_column(String(40))
    title: Mapped[str] = mapped_column(String(180))
    body: Mapped[str] = mapped_column(Text)
    priority: Mapped[str] = mapped_column(String(20), default="normal")
    entity_type: Mapped[str | None] = mapped_column(String(40))
    entity_id: Mapped[int | None] = mapped_column(Integer)
    requires_ack: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    read_at: Mapped[datetime | None] = mapped_column(DateTime)
    acked_at: Mapped[datetime | None] = mapped_column(DateTime)
    channel: Mapped[str] = mapped_column(String(20), default="in_app")
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime)

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(60), index=True)
    entity_id: Mapped[int | None] = mapped_column(Integer, index=True)
    action: Mapped[str] = mapped_column(String(60))
    old_value: Mapped[dict | None] = mapped_column(JSON)
    new_value: Mapped[dict | None] = mapped_column(JSON)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

class AppSetting(Base):
    __tablename__ = "app_settings"
    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    value_json: Mapped[dict] = mapped_column(JSON)
    updated_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
