from datetime import datetime
from sqlalchemy import select
from core.models import Device, User, MaintenanceRecord, EngineerDepartment, Department, StatusReport
from core.rules import priority_for, work_order_number
from core.services.audit_service import log
from core.services.notification_service import send

def _engineers_for(session, department_id):
    ids = [x[0] for x in session.execute(select(EngineerDepartment.engineer_id).where(EngineerDepartment.department_id == department_id)).all()]
    if not ids: return session.query(User).filter_by(role="engineer", is_active=True).all(), True
    return session.query(User).filter(User.id.in_(ids), User.is_active.is_(True)).all(), False

def create_fault(session, reporter: User, device_id: int, severity: str, symptom_text: str = "", origin="nurse_fault"):
    device = session.get(Device, device_id)
    if not device or not device.is_active: raise ValueError("Device not found")
    if reporter.role == "nurse" and reporter.department_id != device.department_id: raise PermissionError("Nurse cannot report outside own department")
    if reporter.role not in {"nurse", "engineer"}: raise PermissionError("Not permitted")
    existing = session.query(MaintenanceRecord).filter(MaintenanceRecord.device_id == device.id, MaintenanceRecord.type == "corrective", MaintenanceRecord.status.in_(["open", "acknowledged", "in_progress", "waiting_parts"])).order_by(MaintenanceRecord.reported_at.desc()).first()
    priority = priority_for(device.risk_class, severity)
    if existing:
        existing.symptom_text = (existing.symptom_text or "") + f"\nبلاغ إضافي: {symptom_text}".strip()
        if priority < existing.priority: existing.priority = priority
        log(session, "work_order", existing.id, "duplicate_fault_appended", reporter.id, new_value={"symptom": symptom_text})
        return existing
    year = datetime.utcnow().year
    seq = session.query(MaintenanceRecord).filter(MaintenanceRecord.wo_number.like(f"WO-{year}-%")).count() + 1
    wo = MaintenanceRecord(wo_number=work_order_number(year, seq), device_id=device.id, type="corrective", origin=origin, priority=priority, severity=severity, status="open", reported_by=reporter.id, symptom_text=symptom_text, reported_at=datetime.utcnow())
    session.add(wo); session.flush()
    if priority in {"P1", "P2"}:
        old = device.status; device.status = "reported_faulty"
        session.add(StatusReport(device_id=device.id, status=device.status, previous_status=old, source="nurse_fault", reported_by=reporter.id, maintenance_record_id=wo.id, note=symptom_text))
        nurses = session.query(User).filter_by(role="nurse", department_id=device.department_id, is_active=True).all()
        for nurse in nurses: send(session, nurse.id, "device_unavailable", "جهاز غير متاح", f"الجهاز {device.name} غير متاح للاستخدام", "urgent", "device", device.id)
    engineers, fallback = _engineers_for(session, device.department_id)
    urgent = priority in {"P1", "P2"}
    for engineer in engineers:
        send(session, engineer.id, "fault_p1" if priority == "P1" else "fault_p2" if priority == "P2" else "fault_p3_p4", "بلاغ عطل جديد", f"{wo.wo_number} — {device.name}: {symptom_text}", "urgent" if urgent else "normal", "work_order", wo.id, requires_ack=priority == "P1")
    if priority == "P1" and device.risk_class == "very_high" or fallback:
        for supervisor in session.query(User).filter_by(role="supervisor", is_active=True).all():
            send(session, supervisor.id, "no_engineer_assigned" if fallback else "fault_p1", "تنبيه صيانة عاجل", f"{wo.wo_number} — {device.name}", "urgent", "work_order", wo.id, requires_ack=priority == "P1")
    log(session, "work_order", wo.id, "created", reporter.id, new_value={"wo_number": wo.wo_number, "priority": priority, "severity": severity})
    return wo
