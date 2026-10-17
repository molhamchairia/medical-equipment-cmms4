from datetime import datetime, timedelta
from core.models import Device, DeviceCategory, Department, MaintenanceSchedule, StatusReport, EngineerDepartment
from core.rules import validate_transition
from core.config import DEFAULT_SETTINGS
from core.services.audit_service import log

ROLE_WRITE = {"engineer", "supervisor"}
def _require(user, roles):
    if not user or user.role not in roles: raise PermissionError("Not permitted")

def list_devices(session, user, department_id=None, include_inactive=False):
    q = session.query(Device)
    if not include_inactive: q = q.filter(Device.is_active.is_(True))
    if user.role == "nurse": q = q.filter(Device.department_id == user.department_id)
    elif department_id: q = q.filter(Device.department_id == department_id)
    return q.order_by(Device.department_id, Device.category_id, Device.name).limit(500).all()

def create_device(session, user, **fields):
    _require(user, ROLE_WRITE)
    category = session.get(DeviceCategory, fields["category_id"])
    if not category: raise ValueError("Unknown category")
    dept = session.get(Department, fields['department_id'])
    if not dept: raise ValueError("Unknown department")
    count = session.query(Device).filter_by(department_id=dept.id, category_id=category.id).count() + 1
    short = ''.join(part[0] for part in category.name_en.split() if part)[:3].upper() or "DEV"
    tag = f"{dept.code}-{short}-{count:03d}"
    device = Device(asset_tag=tag, qr_code_value=tag, name=fields["name"], category_id=category.id, department_id=dept.id,
        risk_class=fields.get("risk_class") or category.default_risk_class, status="operational", room_location=fields.get("room_location"),
        manufacturer=fields.get("manufacturer"), model=fields.get("model"), serial_number=fields.get("serial_number"),
        pm_interval_days=fields.get("pm_interval_days") or category.default_pm_interval_days or DEFAULT_SETTINGS["pm_default_days"][fields.get("risk_class") or category.default_risk_class],
        pm_interval_source=fields.get("pm_interval_source", "standard"), notes=fields.get("notes"), acquisition_source=fields.get("acquisition_source", "unknown"))
    session.add(device); session.flush()
    due = datetime.utcnow() + timedelta(days=device.pm_interval_days)
    session.add(MaintenanceSchedule(device_id=device.id, type="preventive", interval_days=device.pm_interval_days, interval_source=device.pm_interval_source, next_due_at=due))
    session.add(StatusReport(device_id=device.id, status="operational", previous_status=None, source="system", reported_by=user.id, note="Device registered"))
    log(session, "device", device.id, "created", user.id, new_value={"asset_tag": tag, "name": device.name})
    return device

def change_status(session, user, device, new_status, source="engineer", note=None, maintenance_record_id=None):
    _require(user, ROLE_WRITE)
    validate_transition(device.status, new_status)
    old = device.status; device.status = new_status
    session.add(StatusReport(device_id=device.id, status=new_status, previous_status=old, source=source, reported_by=user.id, maintenance_record_id=maintenance_record_id, note=note))
    log(session, "device", device.id, "status_changed", user.id, old_value={"status": old}, new_value={"status": new_status})
