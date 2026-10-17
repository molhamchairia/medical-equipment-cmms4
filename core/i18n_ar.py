"""All user-facing Arabic labels live here."""
STRINGS = {
    "app_title": "نظام إدارة صيانة الأجهزة الطبية",
    "subtitle": "منصة محلية لإدارة الأجهزة والصيانة الوقائية والبلاغات",
    "login": "تسجيل الدخول", "username": "اسم المستخدم", "password": "كلمة المرور",
    "logout": "تسجيل الخروج", "dashboard": "لوحة المعلومات", "tasks_now": "مهامي الآن",
    "devices": "سجل الأجهزة", "fault_report": "إبلاغ عن عطل", "work_orders": "صندوق البلاغات",
    "pm": "الصيانة الوقائية", "procurement": "طلبات الشراء", "notifications": "الإشعارات",
    "users": "المستخدمون", "departments": "الأقسام", "settings": "الإعدادات",
    "reports": "التقارير", "save": "حفظ", "cancel": "إلغاء", "search": "بحث",
    "device_name": "اسم الجهاز", "asset_tag": "رقم الأصل", "department": "القسم",
    "category": "الفئة", "room": "الغرفة / الموقع", "risk": "فئة الخطورة", "status": "الحالة",
    "operational": "يعمل", "reported_faulty": "تم الإبلاغ عن عطل", "under_maintenance": "قيد الصيانة",
    "out_of_service": "خارج الخدمة", "decommissioned": "مخرج من الخدمة نهائياً",
    "very_high": "خطورة عالية جداً", "high": "عالية", "medium": "متوسطة", "low": "منخفضة",
    "stopped": "لا يعمل", "degraded": "يعمل بخلل أو إنذار", "cosmetic": "ملاحظة بسيطة",
    "healthy": "سليم", "not_healthy": "غير سليم", "submit": "إرسال", "start_check": "ابدأ الفحص",
    "no_tasks": "لا توجد مهام الآن", "no_devices": "لا توجد أجهزة لعرضها", "my_department_devices": "أجهزة قسمي",
    "engineer": "مهندس طبي", "nurse": "ممرض/ة", "supervisor": "مشرف / إداري", "procurement_role": "مسؤول المشتريات",
    "priority": "الأولوية", "work_order_number": "رقم أمر العمل", "symptom": "وصف العطل",
    "action_taken": "الإجراء المتخذ", "fault_cause": "سبب العطل", "verified": "تم اختبار الجهاز وهو يعمل",
    "acknowledge": "استلمت", "start_repair": "بدء الإصلاح", "waiting_parts": "خارج الخدمة (بانتظار قطعة/قرار)",
    "no_fault_found": "لا يوجد عطل / الجهاز سليم", "create_device": "إضافة جهاز", "create_user": "إضافة مستخدم",
    "full_name": "الاسم الكامل", "role": "الدور", "active": "فعال", "created": "تم الحفظ بنجاح",
    "invalid_login": "بيانات الدخول غير صحيحة أو الحساب غير فعال", "change_password": "تغيير كلمة المرور",
    "new_password": "كلمة المرور الجديدة", "confirm_password": "تأكيد كلمة المرور", "required": "هذا الحقل مطلوب",
    "open_orders": "أوامر العمل المفتوحة", "overdue_pm": "الصيانة الوقائية المتأخرة", "availability": "توفر الأجهزة",
}

def t(key: str) -> str:
    return STRINGS.get(key, key)
