# 🌐 منصة آفاق الفكر - نظام إدارة التبليغات والمهام
## Afaq AlFiker - Department Management Platform

---

## 📋 هيكل المشروع / Project Structure

```
afaq_alfiker/
├── app.py                      ← نقطة التشغيل الرئيسية
├── requirements.txt
├── database/
│   ├── __init__.py
│   └── db.py                   ← قاعدة البيانات SQLite + النماذج
├── routes/
│   ├── __init__.py
│   ├── auth.py                 ← تسجيل الدخول / الخروج + الحماية
│   ├── dashboard.py            ← لوحة التحكم
│   ├── announcements.py        ← التبليغات + التعليقات
│   ├── tasks.py                ← المهام
│   └── admin.py                ← إدارة النظام (سوبر أدمن فقط)
├── static/
│   ├── css/
│   │   └── main.css            ← تصميم كامل بدعم RTL
│   └── js/
│       └── main.js             ← تفاعل الواجهة
└── templates/
    ├── base.html               ← القالب الأساسي (sidebar + topbar)
    ├── login.html
    ├── dashboard.html
    ├── announcements/
    │   ├── index.html
    │   ├── detail.html
    │   └── create.html
    ├── tasks/
    │   ├── index.html
    │   └── create.html
    └── admin/
        └── index.html
```

---

## 🚀 تشغيل المشروع

```bash
# 1. تثبيت المتطلبات
pip install flask

# 2. تشغيل التطبيق
python app.py

# 3. افتح المتصفح على
http://localhost:5000
```

---

## 👥 بيانات الدخول الافتراضية

### سوبر أدمن
| المستخدم    | كلمة المرور  |
|-------------|--------------|
| superadmin  | Admin@2025!  |

### مدراء الأقسام
| المستخدم   | كلمة المرور | القسم                  |
|------------|-------------|------------------------|
| sales_mgr  | Mgr@Sales1  | المبيعات               |
| cc_mgr     | Mgr@CC2025  | كول سنتر / خدمة العملاء |
| audit_mgr  | Mgr@Audit1  | التدقيق                |
| cash_mgr   | Mgr@Cash22  | الكاشير                |

### الموظفون
| المستخدم    | كلمة المرور | القسم                  |
|-------------|-------------|------------------------|
| emp_sales1  | Emp@123     | المبيعات               |
| emp_cc1     | Emp@123     | كول سنتر               |
| emp_audit1  | Emp@123     | التدقيق                |
| emp_cash1   | Emp@123     | الكاشير                |

---

## 🔐 نظام الصلاحيات

| الصلاحية     | التبليغات              | المهام                   | الإدارة               |
|--------------|------------------------|--------------------------|------------------------|
| superadmin   | عرض/نشر/حذف كل الأقسام | إنشاء/عرض/حذف كل الأقسام | إدارة كاملة للنظام    |
| manager      | نشر/حذف في قسمه فقط   | إنشاء/تعديل في قسمه فقط  | لا                    |
| employee     | عرض + تعليق فقط        | عرض مهامه فقط            | لا                    |

### ✅ الأمان:
- الأقسام معزولة تماماً (موظف قسم A لا يرى قسم B)
- كلمات المرور مشفرة بـ SHA-256
- سجل نشاط كامل (audit log)
- تحقق من الصلاحيات على كل route
- منع CSRF بالـ session key

---

## ➕ إضافة قسم جديد

من لوحة السوبر أدمن ← تبويب "الأقسام" ← أدخل:
- الاسم الإنجليزي (مثال: `hr`)
- الاسم العربي (مثال: `قسم الموارد البشرية`)
- أيقونة FontAwesome (مثال: `fas fa-users-cog`)
- اللون

ثم أضف مدير وموظفين للقسم الجديد من تبويب "المستخدمون".

---

## 🛠️ التقنيات المستخدمة

- **Backend**: Python Flask
- **Database**: SQLite (يمكن ترقيته لـ PostgreSQL)
- **Frontend**: HTML5 + CSS3 (RTL) + JavaScript (Vanilla)
- **Icons**: Font Awesome 6
- **Fonts**: Tajawal (Google Fonts - عربي)
