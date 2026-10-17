from datetime import datetime
from core.models import MaintenanceRecord, Device, User, StatusReport, ProcurementRequest
from core.services.audit_service import log
from core.services.notification_service import send
from core.services.device_service import change_status

ACTIVE = {"open", "acknowledged", "in_progress", "waiting_parts"}
def _check_engineer(session, user, device):
    if user.role not in {"engineer", "supervisor"}: raise PermissionError("Not permitted")
    if user.role == "engineer":
        from core.models import EngineerDepartment
        assigned = session.query(EngineerDepartment).filter_by(engineer_id=user.id, department_id=device.department_id).first()
        if not assigned: raise PermissionError("Engineer is not assigned to this department")

def acknowledge(session, user, wo):
    _check_engineer(session, user, wo.device)
    if wo.status != "open": raise ValueError("Work order is not open")
    wo.status="acknowledged"; wo.acknowledged_at=datetime.utcnow(); wo.assigned_engineer_id=user.id
    log(session,"work_order",wo.id,"acknowledged",user.id,new_value={"status":wo.status})

def triage(session, user, wo, outcome):
    _check_engineer(session, user, wo.device)
    if wo.status not in {"open", "acknowledged"}: raise ValueError("Work order cannot be triaged in this state")
    if outcome == "no_fault_found":
        wo.status="completed"; wo.completed_at=datetime.utcnow(); wo.fault_cause_code="no_fault_found"; wo.action_taken="تم الفحص ولم يظهر عطل"; wo.verified_functional=True
        change_status(session,user,wo.device,"operational",note="No fault found",maintenance_record_id=wo.id)
    elif outcome == "start_repair":
        wo.status="in_progress"; wo.started_at=datetime.utcnow()
        change_status(session,user,wo.device,"under_maintenance",note="Repair started",maintenance_record_id=wo.id)
    elif outcome == "waiting_parts":
        wo.status="waiting_parts"
        change_status(session,user,wo.device,"out_of_service",note="Waiting for parts/decision",maintenance_record_id=wo.id)
    else: raise ValueError("Unknown triage outcome")
    _notify_nurses(session, wo, "تحديث حالة الجهاز")
    log(session,"work_order",wo.id,"triaged",user.id,new_value={"status":wo.status})

def resume_repair(session, user, wo):
    _check_engineer(session, user, wo.device)
    if wo.status != "waiting_parts":
        raise ValueError("Work order is not waiting for parts")
    wo.status = "in_progress"
    if not wo.started_at:
        wo.started_at = datetime.utcnow()
    change_status(session, user, wo.device, "under_maintenance", note="Repair resumed after parts", maintenance_record_id=wo.id)
    _notify_nurses(session, wo, "استؤنف إصلاح الجهاز")
    log(session, "work_order", wo.id, "resume_repair", user.id, new_value={"status": wo.status})


def complete(session, user, wo, fault_cause_code, action_taken, verified_functional, parts_used=None, labor_minutes=None, note=None):
    _check_engineer(session, user, wo.device)
    if wo.status != "in_progress": raise ValueError("Only in-progress work orders can be completed")
    if not fault_cause_code or not action_taken.strip() or not verified_functional: raise ValueError("Cause, action, and functional verification are required")
    wo.status="completed"; wo.completed_at=datetime.utcnow(); wo.fault_cause_code=fault_cause_code; wo.action_taken=action_taken.strip(); wo.verified_functional=True; wo.parts_used=parts_used; wo.labor_minutes=labor_minutes; wo.completion_note=note
    change_status(session,user,wo.device,"operational",note="Repair verified",maintenance_record_id=wo.id)
    _notify_nurses(session, wo, "عاد الجهاز للخدمة")
    send(session, wo.reported_by, "device_back_in_service", "عاد الجهاز للخدمة", f"الجهاز {wo.device.name} عاد للخدمة", "normal", "device", wo.device_id)
    if wo.schedule_id:
        from core.models import MaintenanceSchedule
        schedule=session.get(MaintenanceSchedule,wo.schedule_id)
        if schedule:
            from datetime import timedelta
            schedule.last_done_at=wo.completed_at; schedule.next_due_at=wo.completed_at+timedelta(days=schedule.interval_days)
    log(session,"work_order",wo.id,"completed",user.id,new_value={"status":wo.status,"fault_cause_code":fault_cause_code,"verified_functional":True})

def _notify_nurses(session, wo, title):
    for nurse in session.query(User).filter_by(role="nurse", department_id=wo.device.department_id, is_active=True).all():
        send(session,nurse.id,"device_status_changed",title,f"الجهاز {wo.device.name}: {wo.device.status}","normal","device",wo.device_id)

def create_procurement_request(session, user, wo, item_description, quantity=1, currency="USD", estimated_cost=None):
    if user.role != "engineer": raise PermissionError("Only engineers can request parts")
    if wo.status != "waiting_parts": raise ValueError("Work order must be waiting for parts")
    year=datetime.utcnow().year
    seq=session.query(ProcurementRequest).filter(ProcurementRequest.pr_number.like(f"PR-{year}-%")).count()+1
    req=ProcurementRequest(pr_number=f"PR-{year}-{seq:06d}",maintenance_record_id=wo.id,device_id=wo.device_id,requested_by=user.id,item_description=item_description,quantity=max(1,int(quantity)),urgency=wo.priority,currency=currency,estimated_cost=estimated_cost)
    session.add(req); session.flush()
    for p in session.query(User).filter_by(role="procurement",is_active=True).all(): send(session,p.id,"procurement_new","طلب شراء جديد",f"{req.pr_number} — {item_description}","urgent" if wo.priority in {"P1","P2"} else "normal","procurement",req.id)
    log(session,"procurement",req.id,"created",user.id,new_value={"pr_number":req.pr_number})
    return req
