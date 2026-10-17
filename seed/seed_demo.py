from datetime import datetime, timedelta
from core.db import init_db, session_scope
from core.models import Department, User, EngineerDepartment, DeviceCategory, Device, MaintenanceSchedule, ChecklistTemplate, ChecklistItem, StatusReport
from core.auth import hash_password
from core.config import DEFAULT_SETTINGS

DEPARTMENTS=[("العناية المشددة","ICU","Intensive Care"),("الباطنية","INT","Internal Medicine"),("الإسعاف","ER","Emergency"),("العمليات","OR","Operating Rooms"),("حواضن الخدج","NICU","Neonatal ICU"),("الغسيل الكلوي","DIAL","Dialysis")]
CATEGORIES=[("جهاز تنفس صناعي","Ventilator","very_high",90,[("الجهاز يعمل ولا تظهر رسالة خطأ","stopped"),("البطارية مشحونة","degraded"),("الكابلات والأنابيب سليمة","degraded"),("الشاشة والإنذارات تعمل","stopped"),("الجهاز نظيف ولا يوجد تلف ظاهر","cosmetic")]),("مزيل رجفان","Defibrillator","very_high",90,[ ("الجهاز يعمل واجتاز الاختبار الذاتي","stopped"),("البطارية مشحونة","degraded"),("الأقطاب والكابلات سليمة","degraded"),("الشاشة والإنذارات تعمل","stopped"),("لا يوجد تلف ظاهر","cosmetic")]),("مراقب مريض","Patient Monitor","high",180,[("الشاشة تعمل بوضوح","stopped"),("الكابلات والمجسات سليمة","degraded"),("الإنذارات تعمل","stopped"),("البطارية تعمل","degraded"),("لا يوجد تلف ظاهر","cosmetic")]),("مضخة تسريب","Infusion Pump","high",180,[("الجهاز يعمل ولا يظهر إنذار خطأ","stopped"),("البطارية تعمل","degraded"),("الكابل سليم","degraded"),("الأزرار والشاشة تعمل","degraded"),("الجهاز نظيف","cosmetic")]),("حاضنة أطفال","Neonatal Incubator","very_high",90,[("الجهاز يعمل دون إنذار","stopped"),("الشاشة تعمل","stopped"),("البطارية/مصدر الطاقة سليم","degraded"),("الغطاء والأقفال سليمة","degraded"),("لا يوجد تلف أو تلوث ظاهر","cosmetic")]),("جهاز تخطيط قلب","ECG Machine","medium",365,[])]

def seed_if_empty(demo_mode=None):
    if demo_mode is None:
        import os
        demo_mode = os.environ.get("DEMO_MODE", "false").strip().lower() in {"1", "true", "yes", "on"}
        try:
            import streamlit as st
            demo_mode = str(st.secrets.get("DEMO_MODE", demo_mode)).strip().lower() in {"1", "true", "yes", "on"}
        except Exception:
            pass
    init_db()
    with session_scope() as s:
        if s.query(User).count():
            print("Demo data already exists; no changes made."); return
        deps=[]
        for ar,code,en in DEPARTMENTS:
            d=Department(name_ar=ar,name_en=en,code=code); s.add(d); deps.append(d)
        s.flush()
        users=[User(username="supervisor",full_name="مدير النظام",password_hash=hash_password("ChangeMe123!"),role="supervisor",must_change_password=not demo_mode),
               User(username="engineer1",full_name="المهندس الطبي الأول",password_hash=hash_password("ChangeMe123!"),role="engineer",must_change_password=not demo_mode),
               User(username="engineer2",full_name="المهندس الطبي الثاني",password_hash=hash_password("ChangeMe123!"),role="engineer",must_change_password=not demo_mode),
               User(username="nurse1",full_name="ممرض العناية",password_hash=hash_password("ChangeMe123!"),role="nurse",department_id=deps[0].id,must_change_password=not demo_mode),
               User(username="nurse2",full_name="ممرض الباطنية",password_hash=hash_password("ChangeMe123!"),role="nurse",department_id=deps[1].id,must_change_password=not demo_mode),
               User(username="nurse3",full_name="ممرض الإسعاف",password_hash=hash_password("ChangeMe123!"),role="nurse",department_id=deps[2].id,must_change_password=not demo_mode),
               User(username="procurement",full_name="مسؤول المشتريات",password_hash=hash_password("ChangeMe123!"),role="procurement",must_change_password=not demo_mode)]
        s.add_all(users); s.flush()
        s.add_all([EngineerDepartment(engineer_id=users[1].id,department_id=deps[0].id),EngineerDepartment(engineer_id=users[1].id,department_id=deps[1].id),EngineerDepartment(engineer_id=users[2].id,department_id=deps[2].id),EngineerDepartment(engineer_id=users[2].id,department_id=deps[3].id),EngineerDepartment(engineer_id=users[2].id,department_id=deps[4].id),EngineerDepartment(engineer_id=users[1].id,department_id=deps[5].id)])
        cats=[]
        for ar,en,risk,interval,items in CATEGORIES:
            c=DeviceCategory(name_ar=ar,name_en=en,default_risk_class=risk,default_pm_interval_days=interval); s.add(c); cats.append((c,items))
        s.flush()
        templates={}
        for c,items in cats:
            if not items: items=[("مصدر الطاقة والكابل سليم","degraded"),("الشاشة والمؤشرات تعمل","stopped"),("الملحقات سليمة","degraded"),("لا يوجد تلف ظاهر","cosmetic"),("الجهاز نظيف","cosmetic")]
            template=ChecklistTemplate(category_id=c.id,version=1,is_active=True); s.add(template); s.flush()
            templates[c.id]=template
            for order,(text,severity) in enumerate(items,1): s.add(ChecklistItem(template_id=template.id,sort_order=order,text_ar=text,fail_severity=severity,is_required=True))
        for idx in range(30):
            c,items=cats[idx%len(cats)]; dep=deps[idx%len(deps)]
            short=''.join(p[0] for p in c.name_en.split())[:3].upper()
            tag=f"{dep.code}-{short}-{idx+1:03d}"
            device=Device(asset_tag=tag,qr_code_value=tag,name=f"{c.name_ar} {idx+1}",category_id=c.id,department_id=dep.id,room_location=f"غرفة {idx%8+1}",manufacturer="Demo Medical",model="M-100",serial_number=f"DEMO-{idx+1:04d}",risk_class=c.default_risk_class,status="operational",pm_interval_days=c.default_pm_interval_days or DEFAULT_SETTINGS['pm_default_days'][c.default_risk_class],pm_interval_source="standard",acquisition_source="unknown",is_active=True)
            s.add(device); s.flush()
            s.add(MaintenanceSchedule(device_id=device.id,type="preventive",interval_days=device.pm_interval_days,interval_source="standard",next_due_at=datetime.utcnow()+timedelta(days=device.pm_interval_days)))
            s.add(StatusReport(device_id=device.id,status="operational",source="system",note="Seeded demo device"))
        print("Demo hospital seeded. Temporary password for all accounts: ChangeMe123!" + ("" if demo_mode else " Change it on first login."))

def main():
    seed_if_empty()

if __name__ == "__main__":
    main()
