from datetime import datetime
from zoneinfo import ZoneInfo
from core.models import Device, NursingCheck, NursingCheckResult, ChecklistTemplate, ChecklistItem, StatusReport, User
from core.rules import inspection_policy, current_window, SEVERITY_RANK
from core.services.fault_service import create_fault
from core.services.audit_service import log

def due_devices(session, nurse, now=None):
    if nurse.role != "nurse": raise PermissionError("Only nurses can view inspection tasks")
    now = now or datetime.now(ZoneInfo("Asia/Damascus"))
    devices=session.query(Device).filter_by(department_id=nurse.department_id,is_active=True,status="operational").all()
    due=[]
    for device in devices:
        policy=inspection_policy(device.risk_class,device.inspection_policy_override)
        if policy == "none": continue
        shift,start,end=current_window(now,policy)
        check=session.query(NursingCheck).filter_by(device_id=device.id,nurse_id=nurse.id,window_start=start,window_end=end).first()
        # Window compliance is department-wide, so any check on the device/window removes it from due list.
        any_check=session.query(NursingCheck).filter_by(device_id=device.id,window_start=start,window_end=end).first()
        if not any_check: due.append((device,shift,start,end))
    return sorted(due,key=lambda row:(0 if row[0].risk_class=="very_high" else 1,row[0].name))

def submit_check(session, nurse, device_id, answers: dict[int, tuple[str, str | None]], bulk_ok=False, now=None):
    if nurse.role != "nurse": raise PermissionError("Only nurses can submit checks")
    device=session.get(Device,device_id)
    if not device or device.department_id != nurse.department_id: raise PermissionError("Device outside nurse department")
    if device.status != "operational": raise ValueError("Device is unavailable and cannot be checked")
    policy=inspection_policy(device.risk_class,device.inspection_policy_override)
    if policy == "none": raise ValueError("This device does not require nurse inspection")
    now=now or datetime.now(ZoneInfo("Asia/Damascus")); shift,start,end=current_window(now,policy)
    if session.query(NursingCheck).filter_by(device_id=device.id,window_start=start,window_end=end).first(): raise ValueError("This device was already checked in this window")
    template=session.query(ChecklistTemplate).filter_by(category_id=device.category_id,is_active=True).order_by(ChecklistTemplate.version.desc()).first()
    items=session.query(ChecklistItem).filter_by(template_id=template.id).order_by(ChecklistItem.sort_order).all() if template else []
    for item in items:
        if item.is_required and item.id not in answers: raise ValueError("Every required checklist item must be answered")
    if not items and not answers: raise ValueError("No checklist items configured")
    failed=[]
    for item in items:
        answer=answers.get(item.id)
        if answer and answer[0] == "not_ok": failed.append((item,answer[1]))
    check=NursingCheck(device_id=device.id,nurse_id=nurse.id,department_id=nurse.department_id,shift=shift,window_start=start,window_end=end,overall_result="issues" if failed else "ok",bulk_ok=bulk_ok,template_id=template.id if template else None,template_version=template.version if template else 1)
    session.add(check); session.flush()
    for item in items:
        result,note=answers[item.id]
        session.add(NursingCheckResult(check_id=check.id,item_id=item.id,result=result,note=note))
    if failed:
        worst=max((x[0].fail_severity for x in failed),key=lambda s:SEVERITY_RANK[s])
        symptom="؛ ".join(item.text_ar + (f" — {note}" if note else "") for item,note in failed)
        wo=create_fault(session,nurse,device.id,worst,symptom,origin="nurse_check"); wo.nursing_check_id=check.id
    elif device.status == "operational":
        session.add(StatusReport(device_id=device.id,status="operational",previous_status="operational",source="nurse_auto",reported_by=nurse.id,nursing_check_id=check.id,note="All checklist items OK"))
        wo=None
    log(session,"nursing_check",check.id,"submitted",nurse.id,new_value={"result":check.overall_result,"bulk_ok":bulk_ok})
    return check, (wo if failed else None)
