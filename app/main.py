import streamlit as st
from sqlalchemy import func
from core.db import init_db, SessionLocal
from core.auth import authenticate, change_password
from core.i18n_ar import t
from core.models import User, Device, MaintenanceRecord, MaintenanceSchedule, Department, DeviceCategory, Notification, ProcurementRequest, ChecklistTemplate, ChecklistItem, NursingCheck
from core.services.device_service import list_devices, create_device
from core.services.fault_service import create_fault
from core.services.inspection_service import due_devices, submit_check
from core.services.workorder_service import acknowledge, triage, complete, create_procurement_request, resume_repair
from core.services.notification_service import mark_read
from app.ui.theme import apply_theme

import os
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

def _demo_mode():
    value = os.environ.get("DEMO_MODE", "false")
    try:
        value = st.secrets.get("DEMO_MODE", value)
    except Exception:
        pass
    return str(value).strip().lower() in {"1", "true", "yes", "on"}

def _initialize_app():
    @st.cache_resource
    def initialize():
        init_db()
        from seed.seed_demo import seed_if_empty
        seed_if_empty(demo_mode=_demo_mode())
    initialize()

def run():
    st.set_page_config(page_title="نظام إدارة صيانة الأجهزة الطبية", page_icon="🏥", layout="wide", initial_sidebar_state="collapsed")
    apply_theme()
    _initialize_app()
    demo_mode = _demo_mode()
    if demo_mode:
        st.warning("نسخة تجريبية – بيانات وهمية\n\nتُعاد البيانات إلى حالتها الأصلية عند إعادة تشغيل التطبيق.")

    ROLE_PAGES = {
     "nurse": ["مهامي الآن", "إبلاغ عن عطل", "أجهزة قسمي", "الإشعارات", "الملف الشخصي"],
     "engineer": ["صندوق البلاغات", "سجل الأجهزة", "الصيانة الوقائية", "طلبات الشراء", "امتثال الفحوصات", "الإشعارات", "الملف الشخصي"],
     "supervisor": ["لوحة المعلومات", "التصعيدات", "سجل الأجهزة", "المستخدمون", "الأقسام", "التقارير", "الإشعارات", "الملف الشخصي"],
     "procurement": ["طلبات الشراء", "سجل الطلبات", "الإشعارات", "الملف الشخصي"],
    }
    ROLE_AR={"nurse":"ممرض/ة","engineer":"مهندس طبي","supervisor":"مشرف / إداري","procurement":"مسؤول المشتريات"}

    if "user_id" not in st.session_state: st.session_state.user_id=None
    if not st.session_state.user_id:
        st.title(t("app_title")); st.caption(t("subtitle"))
        with st.form("login"):
            username=st.text_input(t("username")); password=st.text_input(t("password"),type="password")
            submit=st.form_submit_button(t("login"),use_container_width=True)
        if submit:
            with SessionLocal() as s:
                user=authenticate(s,username.strip(),password)
                if user:
                    st.session_state.user_id=user.id; st.rerun()
                else: st.error(t("invalid_login"))
        if demo_mode:
            st.info("حسابات تجريبية: supervisor / engineer1 / nurse1 / procurement — كلمة المرور المشتركة: ChangeMe123!")
        else:
            st.info("يعمل النظام محلياً على شبكة المستشفى. لا يحتاج إلى اتصال بالإنترنت بعد التثبيت.")
        st.stop()

    with SessionLocal() as session:
        user=session.get(User,st.session_state.user_id)
        if not user or not user.is_active:
            st.session_state.user_id=None; st.rerun()
        if user.must_change_password and not demo_mode:
            st.title(t("change_password")); st.warning("يجب تغيير كلمة المرور قبل استخدام النظام.")
            with st.form("force_password"):
                p1=st.text_input(t("new_password"),type="password"); p2=st.text_input(t("confirm_password"),type="password")
                ok=st.form_submit_button(t("save"),use_container_width=True)
            if ok:
                if p1 != p2: st.error("كلمتا المرور غير متطابقتين")
                else:
                    try: change_password(session,user,p1); st.success(t("created")); st.rerun()
                    except ValueError as e: st.error(str(e))
            st.stop()
        with st.sidebar:
            st.markdown(f"### {user.full_name}")
            st.caption(ROLE_AR.get(user.role,user.role)+(f" · {user.department.name_ar}" if user.department else ""))
            page=st.radio("القائمة",ROLE_PAGES[user.role],label_visibility="collapsed")
            if st.button(t("logout"),use_container_width=True): st.session_state.user_id=None; st.rerun()
        st.title(page)
        unread=session.query(Notification).filter_by(recipient_id=user.id,read_at=None).count()
        if unread: st.warning(f"لديك {unread} إشعار غير مقروء")

        if page in ("مهامي الآن",):
            due=due_devices(session,user)
            checked=session.query(NursingCheck).filter_by(nurse_id=user.id).count()
            st.caption(f"الأجهزة المطلوب فحصها الآن: {len(due)}")
            if not due: st.success(t("no_tasks"))
            for device,shift,start,end in due:
                with st.container(border=True):
                    st.subheader(device.name); st.caption(f"{device.asset_tag} · {device.room_location or '—'} · {device.department.name_ar}")
                    st.write(f"الخطورة: {t(device.risk_class)}")
                    if st.button(t("start_check"),key=f"check_{device.id}",use_container_width=True): st.session_state.check_device=device.id; st.rerun()
            if st.session_state.get("check_device"):
                device=session.get(Device,st.session_state.check_device)
                template=session.query(ChecklistTemplate).filter_by(category_id=device.category_id,is_active=True).order_by(ChecklistTemplate.version.desc()).first()
                items=session.query(ChecklistItem).filter_by(template_id=template.id).order_by(ChecklistItem.sort_order).all() if template else []
                st.divider(); st.subheader(f"قائمة فحص: {device.name}")
                with st.form("check_form"):
                    answers={}
                    for item in items:
                        answer=st.radio(item.text_ar,["سليم","غير سليم"],index=None,horizontal=True,key=f"item_{item.id}")
                        note=st.text_input("ملاحظة (اختياري)",key=f"note_{item.id}") if answer=="غير سليم" else None
                        if answer: answers[item.id]=("ok" if answer=="سليم" else "not_ok",note)
                    bulk=st.checkbox("كل شيء سليم (تأكيد سريع)")
                    submitted=st.form_submit_button(t("submit"),use_container_width=True)
                if bulk and submitted:
                    answers={i.id:("ok",None) for i in items}
                if submitted:
                    try:
                        check,wo=submit_check(session,user,device.id,answers,bulk_ok=bulk); session.commit()
                        st.success(f"تم الحفظ — {('بلاغ رقم '+wo.wo_number+' للمهندس') if wo else 'الجهاز سليم'}"); st.session_state.check_device=None; st.rerun()
                    except Exception as e: session.rollback(); st.error(str(e))

        elif page=="إبلاغ عن عطل":
            devices=list_devices(session,user)
            with st.form("fault_form"):
                device_id=st.selectbox("اختر الجهاز",[d.id for d in devices],format_func=lambda x: next((f"{d.asset_tag} — {d.name}" for d in devices if d.id==x),str(x)))
                severity_label=st.radio("نوع العطل",["لا يعمل","يعمل بخلل أو إنذار","ملاحظة بسيطة"],horizontal=False)
                note=st.text_area("ملاحظة إضافية (اختياري)")
                send=st.form_submit_button(t("submit"),use_container_width=True)
            if send:
                severity={"لا يعمل":"stopped","يعمل بخلل أو إنذار":"degraded","ملاحظة بسيطة":"cosmetic"}[severity_label]
                try:
                    wo=create_fault(session,user,device_id,severity,note,origin="nurse_fault"); session.commit(); st.success(f"تم إرسال البلاغ رقم {wo.wo_number}")
                except Exception as e: session.rollback(); st.error(str(e))

        elif page in ("أجهزة قسمي","سجل الأجهزة"):
            devices=list_devices(session,user)
            q=st.text_input(t("search")); devices=[d for d in devices if q.lower() in (d.name+d.asset_tag+(d.serial_number or "")).lower()]
            if page=="سجل الأجهزة" and user.role in {"engineer","supervisor"}:
                with st.expander(t("create_device")):
                    with st.form("new_device"):
                        name=st.text_input(t("device_name")); dept_id=st.selectbox(t("department"),[d.id for d in session.query(Department).filter_by(is_active=True).all()],format_func=lambda x:session.get(Department,x).name_ar)
                        cat_id=st.selectbox(t("category"),[c.id for c in session.query(DeviceCategory).all()],format_func=lambda x:session.get(DeviceCategory,x).name_ar)
                        risk=st.selectbox(t("risk"),["very_high","high","medium","low"],format_func=lambda x:t(x)); room=st.text_input(t("room")); pm=st.number_input("فترة الصيانة الوقائية بالأيام",min_value=1,value=180)
                        save=st.form_submit_button(t("save"),use_container_width=True)
                    if save:
                        try: create_device(session,user,name=name,department_id=dept_id,category_id=cat_id,risk_class=risk,room_location=room,pm_interval_days=int(pm)); session.commit(); st.success(t("created")); st.rerun()
                        except Exception as e: session.rollback(); st.error(str(e))
            if not devices: st.info(t("no_devices"))
            for d in devices:
                with st.container(border=True):
                    st.subheader(d.name); st.caption(f"{d.asset_tag} · {d.department.name_ar} · {d.room_location or '—'}")
                    st.write(f"الحالة: **{t(d.status)}** · الخطورة: **{t(d.risk_class)}**")

        elif page=="صندوق البلاغات":
            q=session.query(MaintenanceRecord).filter(MaintenanceRecord.status.in_(["open","acknowledged","in_progress","waiting_parts"])).order_by(MaintenanceRecord.priority,MaintenanceRecord.reported_at).limit(50).all()
            for wo in q:
                with st.container(border=True):
                    st.subheader(f"{wo.wo_number} · {wo.device.name}"); st.caption(f"{wo.priority} · {wo.status} · {wo.device.department.name_ar}"); st.write(wo.symptom_text or "—")
                    if wo.status=="open" and st.button("استلمت",key=f"ack_{wo.id}"):
                        try: acknowledge(session,user,wo); session.commit(); st.rerun()
                        except Exception as e: session.rollback(); st.error(str(e))
                    if wo.status in {"open","acknowledged"}:
                        c1,c2,c3=st.columns(3)
                        if c1.button("لا يوجد عطل",key=f"none_{wo.id}"):
                            try: triage(session,user,wo,"no_fault_found"); session.commit(); st.rerun()
                            except Exception as e: session.rollback(); st.error(str(e))
                        if c2.button("بدء الإصلاح",key=f"start_{wo.id}"):
                            try: triage(session,user,wo,"start_repair"); session.commit(); st.rerun()
                            except Exception as e: session.rollback(); st.error(str(e))
                        if c3.button("خارج الخدمة",key=f"wait_{wo.id}"):
                            try: triage(session,user,wo,"waiting_parts"); session.commit(); st.rerun()
                            except Exception as e: session.rollback(); st.error(str(e))
                    if wo.status=="waiting_parts" and st.button("استئناف الإصلاح", key=f"resume_{wo.id}"):
                        try: resume_repair(session,user,wo); session.commit(); st.rerun()
                        except Exception as e: session.rollback(); st.error(str(e))
                    if wo.status=="in_progress":
                        with st.form(f"complete_{wo.id}"):
                            cause=st.selectbox("سبب العطل",["user_error","power_supply","battery","cable_accessory","sensor_probe","software_firmware","mechanical_wear","calibration_drift","electronic_component","leak_or_fluid","physical_damage","consumable_depleted","scheduled_pm","other"],key=f"cause_{wo.id}")
                            action=st.text_area("الإجراء المتخذ",key=f"action_{wo.id}"); parts=st.text_input("القطع المستخدمة (اختياري)",key=f"parts_{wo.id}"); verified=st.checkbox("تم اختبار الجهاز وهو يعمل",key=f"verified_{wo.id}")
                            done=st.form_submit_button("إكمال أمر العمل",use_container_width=True)
                        if done:
                            try: complete(session,user,wo,cause,action,verified,parts_used=parts); session.commit(); st.success("تم إكمال أمر العمل"); st.rerun()
                            except Exception as e: session.rollback(); st.error(str(e))
                    if wo.status=="waiting_parts":
                        with st.expander("إنشاء طلب شراء"):
                            with st.form(f"pr_{wo.id}"):
                                item=st.text_input("القطعة المطلوبة"); qty=st.number_input("الكمية",min_value=1,value=1); currency=st.selectbox("العملة",["USD","SYP"]); create=st.form_submit_button("إنشاء الطلب")
                            if create:
                                try: req=create_procurement_request(session,user,wo,item,int(qty),currency); session.commit(); st.success(f"تم إنشاء {req.pr_number}"); st.rerun()
                                except Exception as e: session.rollback(); st.error(str(e))

        elif page in ("الصيانة الوقائية",):
            schedules=session.query(MaintenanceSchedule).filter_by(is_active=True).order_by(MaintenanceSchedule.next_due_at).limit(50).all()
            for x in schedules: st.write(f"**{x.device.name}** · {x.device.asset_tag} · الاستحقاق: {x.next_due_at:%Y-%m-%d} · كل {x.interval_days} يوم")
        elif page in ("طلبات الشراء","سجل الطلبات"):
            reqs=session.query(ProcurementRequest).order_by(ProcurementRequest.created_at.desc()).limit(50).all()
            for r in reqs:
                with st.container(border=True):
                    st.subheader(f"{r.pr_number} · {r.item_description}"); st.caption(f"{r.device.name} · {r.status} · الأولوية {r.urgency} · الكمية {r.quantity}")
                    if user.role=="procurement" and not demo_mode and r.status in {"requested","ordered"}:
                        if r.status=="requested":
                            supplier=st.text_input("المورد",key=f"supplier_{r.id}")
                            if st.button("تأكيد الطلب",key=f"order_{r.id}"):
                                from datetime import datetime
                                r.status="ordered"; r.supplier=supplier; r.ordered_at=datetime.utcnow(); session.commit(); st.rerun()
                        if r.status=="ordered" and st.button("تم التسليم",key=f"delivered_{r.id}"):
                            from datetime import datetime
                            r.status="delivered"; r.delivered_at=datetime.utcnow(); session.commit(); st.rerun()
                        if st.button("إلغاء الطلب",key=f"cancel_{r.id}"):
                            r.status="cancelled"; r.note="تم الإلغاء من شاشة المشتريات"; session.commit(); st.rerun()

        elif page in ("لوحة المعلومات","التصعيدات","امتثال الفحوصات","التقارير"):
            active=session.query(Device).filter_by(is_active=True).count(); operational=session.query(Device).filter_by(is_active=True,status="operational").count()
            open_wo=session.query(MaintenanceRecord).filter(MaintenanceRecord.status.in_(["open","acknowledged","in_progress","waiting_parts"])).count()
            overdue=session.query(MaintenanceSchedule).filter(MaintenanceSchedule.is_active.is_(True),MaintenanceSchedule.next_due_at < __import__('datetime').datetime.utcnow()).count()
            a,b,c=st.columns(3); a.metric("الأجهزة المتاحة",f"{operational}/{active}"); b.metric(t("open_orders"),open_wo); c.metric(t("overdue_pm"),overdue)
            st.subheader("الأجهزة حسب الحالة")
            status_counts={t(x):session.query(Device).filter_by(status=x,is_active=True).count() for x in ["operational","reported_faulty","under_maintenance","out_of_service","decommissioned"]}
            st.bar_chart(status_counts)
            if page=="التقارير" and user.role in {"engineer","supervisor"}:
                import csv,io
                output=io.StringIO(); writer=csv.writer(output); writer.writerow(["asset_tag","name","department","category","risk_class","status"])
                for d in session.query(Device).all(): writer.writerow([d.asset_tag,d.name,d.department.name_ar,d.category.name_ar,d.risk_class,d.status])
                st.download_button("تصدير سجل الأجهزة CSV",output.getvalue().encode("utf-8-sig"),file_name="devices.csv",mime="text/csv")
        elif page=="المستخدمون" and user.role=="supervisor":
            with st.expander(t("create_user")) if not demo_mode else st.expander("إدارة المستخدمين (قراءة فقط)"):
                with st.form("new_user") if not demo_mode else st.form("new_user_readonly"):
                    username=st.text_input(t("username")); name=st.text_input(t("full_name")); role=st.selectbox(t("role"),["nurse","engineer","supervisor","procurement"],format_func=lambda x:ROLE_AR[x]); dept_options=session.query(Department).filter_by(is_active=True).all(); dept=st.selectbox(t("department"),[None]+[d.id for d in dept_options],format_func=lambda x:"—" if x is None else session.get(Department,x).name_ar); save=st.form_submit_button(t("save"))
                if save and not demo_mode:
                    from core.auth import hash_password
                    if not username or not name: st.error(t("required"))
                    elif session.query(User).filter_by(username=username).first(): st.error("اسم المستخدم موجود مسبقاً")
                    else: session.add(User(username=username,full_name=name,role=role,department_id=dept,password_hash=hash_password("ChangeMe123!"),must_change_password=True)); session.commit(); st.success("تم إنشاء المستخدم. كلمة المرور المؤقتة: ChangeMe123!"); st.rerun()
            for u in session.query(User).order_by(User.role,User.full_name).all(): st.write(f"{u.full_name} · {ROLE_AR.get(u.role,u.role)} · {'فعال' if u.is_active else 'معطل'}")
        elif page=="الأقسام" and user.role=="supervisor":
            with st.form("new_dept") if not demo_mode else st.form("new_dept_readonly"):
                ar=st.text_input("اسم القسم بالعربية"); en=st.text_input("اسم القسم بالإنجليزية"); code=st.text_input("الرمز المختصر"); save=st.form_submit_button(t("save"))
            if save and not demo_mode:
                if ar and code: session.add(Department(name_ar=ar,name_en=en,code=code.upper())); session.commit(); st.success(t("created")); st.rerun()
                else: st.error(t("required"))
            for d in session.query(Department).all(): st.write(f"{d.name_ar} ({d.code})")
        elif page=="الإشعارات":
            notices=session.query(Notification).filter_by(recipient_id=user.id).order_by(Notification.read_at.is_(None).desc(),Notification.created_at.desc()).limit(50).all()
            for n in notices:
                with st.container(border=True):
                    st.markdown(f"**{n.title}** {'🔴' if n.priority=='urgent' else ''}"); st.write(n.body); st.caption(n.created_at.strftime("%Y-%m-%d %H:%M"))
                    if n.read_at is None and st.button("تحديد كمقروء",key=f"read_{n.id}"):
                        mark_read(session,n); session.commit(); st.rerun()
                    if n.requires_ack and n.acked_at is None and st.button("استلمت",key=f"acknot_{n.id}"):
                        mark_read(session,n,acknowledge=True); session.commit(); st.rerun()
        elif page=="الملف الشخصي":
            st.write(f"**{user.full_name}** · {ROLE_AR[user.role]}")
            if demo_mode:
                st.info("تغيير كلمة المرور معطل في النسخة التجريبية المشتركة.")
            else:
                with st.form("change_pw"):
                    old=st.text_input("كلمة المرور الحالية",type="password"); new=st.text_input(t("new_password"),type="password"); confirm=st.text_input(t("confirm_password"),type="password"); save=st.form_submit_button(t("save"))
                if save:
                    from core.auth import verify_password
                    if not verify_password(old,user.password_hash): st.error("كلمة المرور الحالية غير صحيحة")
                    elif new!=confirm: st.error("كلمتا المرور غير متطابقتين")
                    else:
                        try: change_password(session,user,new); st.success(t("created")); st.rerun()
                        except Exception as e: st.error(str(e))

if __name__ == "__main__":
    run()
