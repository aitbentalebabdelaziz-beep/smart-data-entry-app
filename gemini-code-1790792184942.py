import streamlit as st
import sqlite3
import pandas as pd
import json
import re
from datetime import datetime

# ==========================================
# 1. PAGE CONFIGURATION
# ==========================================
st.set_page_config(
    page_title="تطبيق إدخال البيانات والذكاء الاصطناعي",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Clean, native-friendly RTL CSS override
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Cairo', sans-serif;
    }
    
    /* Subtle container styling */
    .stCard {
        background-color: #ffffff;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        border: 1px solid #e2e8f0;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. DATABASE SETUP
# ==========================================
DB_NAME = "app_database.db"

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS schema_fields (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            field_name TEXT NOT NULL,
            field_type TEXT NOT NULL,
            options TEXT,
            is_required INTEGER DEFAULT 0
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            data_json TEXT NOT NULL
        )
    ''')

    cursor.execute("SELECT COUNT(*) FROM schema_fields")
    if cursor.fetchone()[0] == 0:
        default_schema = [
            ("اسم العميل / المستفيد", "نص (Text)", "", 1),
            ("رقم الهاتف / التواصل", "رقم (Number)", "", 1),
            ("تصنيف المعاملة", "قائمة خيارات (Dropdown)", "طلب جديد, استفسار, دعم فني, شكوى, صيانة", 1),
            ("حالة الطلب", "قائمة خيارات (Dropdown)", "جديد, قيد المتابعة, مكتمل, معلق", 1),
            ("المبلغ / القيمة", "رقم (Number)", "", 0),
            ("تاريخ المعاملة", "تاريخ (Date)", "", 1),
            ("التفاصيل والملاحظات", "ملاحظات (Text Area)", "", 0)
        ]
        for name, ftype, opts, req in default_schema:
            cursor.execute("INSERT INTO schema_fields (field_name, field_type, options, is_required) VALUES (?, ?, ?, ?)",
                           (name, ftype, opts, req))

    cursor.execute("SELECT COUNT(*) FROM records")
    if cursor.fetchone()[0] == 0:
        sample_data = {
            "اسم العميل / المستفيد": "شركة الأمل للتجارة",
            "رقم الهاتف / التواصل": "0501234567",
            "تصنيف المعاملة": "طلب جديد",
            "حالة الطلب": "جديد",
            "المبلغ / القيمة": 1500,
            "تاريخ المعاملة": str(datetime.now().date()),
            "التفاصيل والملاحظات": "طلب توريد أجهزة ومستلزمات مكتبية"
        }
        cursor.execute("INSERT INTO records (user_email, data_json) VALUES (?, ?)", 
                       ("admin@app.com", json.dumps(sample_data, ensure_ascii=False)))

    conn.commit()
    conn.close()

init_db()

def ai_extract_data(text_input, schema_fields):
    extracted = {}
    text = text_input.strip()
    phone_match = re.search(r'05\d{8}|\+?\d{10,12}', text)
    amount_match = re.search(r'(\d+)\s*(ريال|درهم|دولار|\$)?', text)

    for field in schema_fields:
        fname = field["field_name"]
        ftype = field["field_type"]

        if ("هاتف" in fname or "تواصل" in fname or "رقم" in fname) and ftype == "رقم (Number)":
            extracted[fname] = int(phone_match.group(0)) if phone_match else 0
        elif "مبلغ" in fname or "قيمة" in fname or "سعر" in fname:
            extracted[fname] = int(amount_match.group(1)) if amount_match else 0
        elif ftype == "تاريخ (Date)":
            extracted[fname] = str(datetime.now().date())
        elif ftype == "قائمة خيارات (Dropdown)":
            opts = [o.strip() for o in field["options"].split(",")] if field["options"] else []
            found_opt = opts[0] if opts else ""
            for o in opts:
                if o in text:
                    found_opt = o
                    break
            extracted[fname] = found_opt
        elif ftype == "نص (Text)" and ("اسم" in fname or "عميل" in fname or "مستفيد" in fname):
            words = text.split()
            extracted[fname] = " ".join(words[:2]) if len(words) >= 2 else text
        else:
            extracted[fname] = text

    return extracted

# ==========================================
# 3. SESSION STATE
# ==========================================
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "user_email" not in st.session_state:
    st.session_state["user_email"] = ""
if "ai_prefilled" not in st.session_state:
    st.session_state["ai_prefilled"] = {}

# ==========================================
# 4. LOGIN
# ==========================================
if not st.session_state["logged_in"]:
    st.title("⚡ تسجيل الدخول إلى المنصة")
    st.write("أدخل البريد الإلكتروني للوصول إلى قاعدة البيانات والخدمات الذكية.")

    with st.form("login_form"):
        email_input = st.text_input("📧 البريد الإلكتروني:", placeholder="user@example.com")
        password_input = st.text_input("🔑 كلمة المرور (اختياري):", type="password")
        submit_login = st.form_submit_button("🚀 تسجيل الدخول", use_container_width=True)
        
        if submit_login:
            email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
            if not email_input or not re.match(email_regex, email_input.strip()):
                st.error("⚠️ يرجى إدخال بريد إلكتروني صحيح.")
            else:
                conn = get_db()
                conn.execute("INSERT OR IGNORE INTO users (email) VALUES (?)", (email_input.strip().lower(),))
                conn.commit()
                conn.close()
                st.session_state["logged_in"] = True
                st.session_state["user_email"] = email_input.strip().lower()
                st.success("تم تسجيل الدخول بنجاح!")
                st.rerun()

# ==========================================
# 5. MAIN DASHBOARD
# ==========================================
else:
    st.title("⚡ منصة إدخال البيانات والتطبيقات الذكية")
    st.caption(f"👤 مرحباً بك: **{st.session_state['user_email']}**")
    st.divider()

    with st.sidebar:
        st.header("📋 القائمة الرئيسية")
        app_mode = st.radio(
            "انتقل بين الشاشات:",
            [
                "🏠 الرئيسية والإحصائيات",
                "🤖 المساعد الذكي (AI)",
                "📝 نموذج إدخال جديد",
                "🔍 البحث والتفتيش الفوري",
                "📊 قاعدة البيانات الكاملة",
                "⚙️ إعدادات الحقول"
            ]
        )
        st.divider()
        if st.button("🚪 تسجيل الخروج", use_container_width=True):
            st.session_state["logged_in"] = False
            st.session_state["user_email"] = ""
            st.rerun()

    conn = get_db()
    total_records = conn.execute("SELECT COUNT(*) FROM records").fetchone()[0]
    total_fields = conn.execute("SELECT COUNT(*) FROM schema_fields").fetchone()[0]
    my_records = conn.execute("SELECT COUNT(*) FROM records WHERE user_email = ?", (st.session_state["user_email"],)).fetchone()[0]
    schema_rows = conn.execute("SELECT * FROM schema_fields").fetchall()
    conn.close()

    # 1. HOME DASHBOARD
    if app_mode == "🏠 الرئيسية والإحصائيات":
        st.subheader("📊 نظرة عامة")
        
        c1, c2, c3 = st.columns(3)
        c1.metric("إجمالي السجلات", total_records)
        c2.metric("سجلاتك المدخلة", my_records)
        c3.metric("عدد الحقول النشطة", total_fields)

        st.divider()
        st.subheader("⚡ وصول سريع")
        col_a, col_b = st.columns(2)
        with col_a:
            st.info("💡 **استخراج الذكاء الاصطناعي:** يمكنك لصق رسالة عميل وسيقوم النظام بتفنيطها وتعبئة الحقول أوتوماتيكياً.")
        with col_b:
            st.success("📊 **تصدير البيانات:** يتيح لك النظام تنزيل كافة السجلات بصيغة Excel أو CSV بضغطة زر.")

    # 2. AI ASSISTANT
    elif app_mode == "🤖 المساعد الذكي (AI)":
        st.subheader("🤖 استخراج البيانات التلقائي بالذكاء الاصطناعي")
        
        raw_text = st.text_area("✍️ ألصق نص المعاملة أو الرسالة هنا:", placeholder="مثال: أنا أحمد رقمي 0501234567 أريد طلب جديد بقيمة 1500 ريال", height=120)
        
        if st.button("🪄 تفكيك النص واستخراج الحقول", use_container_width=True):
            if not raw_text.strip():
                st.warning("يرجى كتابة أو لصق نص أولاً.")
            else:
                extracted_data = ai_extract_data(raw_text, schema_rows)
                st.session_state["ai_prefilled"] = extracted_data
                st.success("✅ تم تحليل النص! انتقل الآن لشاشة '📝 نموذج إدخال جديد' لتجد الحقول جاهزة ومملوءة تلقائياً.")
                st.json(extracted_data)

    # 3. FORM ENTRY
    elif app_mode == "📝 نموذج إدخال جديد":
        st.subheader("📝 نموذج إدخال البيانات")

        if st.session_state.get("ai_prefilled"):
            st.info("✨ تم ملء البيانات تلقائياً بواسطة الذكاء الاصطناعي. تحقق منها ثم اضغط حفظ.")

        if not schema_rows:
            st.warning("لم يتم تعيين أي حقول بعد. انتقل إلى '⚙️ إعدادات الحقول' لإضافة حقولك.")
        else:
            with st.form("data_entry_form", clear_on_submit=True):
                form_values = {}
                cols = st.columns(2)
                ai_data = st.session_state.get("ai_prefilled", {})

                for i, field in enumerate(schema_rows):
                    fname = field["field_name"]
                    ftype = field["field_type"]
                    fopts = [o.strip() for o in field["options"].split(",")] if field["options"] else []
                    freq = " *" if field["is_required"] else ""
                    default_val = ai_data.get(fname, "")

                    with cols[i % 2]:
                        if ftype == "نص (Text)":
                            form_values[fname] = st.text_input(f"{fname}{freq}", value=str(default_val))
                        elif ftype == "رقم (Number)":
                            val_num = int(default_val) if str(default_val).isdigit() else 0
                            form_values[fname] = st.number_input(f"{fname}{freq}", value=val_num)
                        elif ftype == "قائمة خيارات (Dropdown)":
                            opts = fopts if fopts else ["افتراضي"]
                            idx = opts.index(default_val) if default_val in opts else 0
                            form_values[fname] = st.selectbox(f"{fname}{freq}", opts, index=idx)
                        elif ftype == "تاريخ (Date)":
                            form_values[fname] = str(st.date_input(f"{fname}{freq}"))
                        elif ftype == "ملاحظات (Text Area)":
                            form_values[fname] = st.text_area(f"{fname}{freq}", value=str(default_val))

                btn_submit = st.form_submit_button("💾 حفظ البيانات", use_container_width=True)
                
                if btn_submit:
                    missing_reqs = []
                    for field in schema_rows:
                        if field["is_required"]:
                            v = form_values.get(field["field_name"])
                            if v is None or str(v).strip() == "":
                                missing_reqs.append(field["field_name"])
                    
                    if missing_reqs:
                        st.error(f"⚠️ يرجى ملء الحقول الإجبارية: {', '.join(missing_reqs)}")
                    else:
                        conn = get_db()
                        conn.execute("INSERT INTO records (user_email, data_json) VALUES (?, ?)",
                                     (st.session_state["user_email"], json.dumps(form_values, ensure_ascii=False)))
                        conn.commit()
                        conn.close()
                        st.session_state["ai_prefilled"] = {}
                        st.success("✅ تم حفظ السجل بنجاح!")

    # 4. SEARCH
    elif app_mode == "🔍 البحث والتفتيش الفوري":
        st.subheader("🔍 البحث والتفتيش في السجلات")
        search_query = st.text_input("🔎 اكتب للبحث (اسم، هاتف، حالة...):")
        
        conn = get_db()
        all_recs = conn.execute("SELECT * FROM records ORDER BY id DESC").fetchall()
        conn.close()

        filtered = []
        for r in all_recs:
            data_dict = json.loads(r["data_json"])
            full_text = f"{r['id']} {r['user_email']} {r['created_at']} " + " ".join([str(v) for v in data_dict.values()])
            if search_query.strip() == "" or search_query.strip().lower() in full_text.lower():
                filtered.append((r, data_dict))

        st.write(f"النتائج: **{len(filtered)}** سجل")
        
        for r, ddict in filtered:
            with st.expander(f"📌 سجل رقم #{r['id']} - مُدخل بواسطة: {r['user_email']}"):
                for k, v in ddict.items():
                    st.write(f"• **{k}:** {v}")
                if st.button(f"🗑️ حذف السجل #{r['id']}", key=f"del_{r['id']}"):
                    conn = get_db()
                    conn.execute("DELETE FROM records WHERE id = ?", (r['id'],))
                    conn.commit()
                    conn.close()
                    st.success("تم الحذف.")
                    st.rerun()

    # 5. DATABASE TABLE
    elif app_mode == "📊 قاعدة البيانات الكاملة":
        st.subheader("📊 استعراض الجدول والتصدير")
        
        conn = get_db()
        recs = conn.execute("SELECT id, user_email, created_at, data_json FROM records ORDER BY id DESC").fetchall()
        conn.close()

        if not recs:
            st.info("لا توجد بيانات مسجلة.")
        else:
            table_data = []
            for r in recs:
                row_dict = {"رقم السجل": r["id"], "المُدخل": r["user_email"], "التاريخ": r["created_at"]}
                row_dict.update(json.loads(r["data_json"]))
                table_data.append(row_dict)

            df = pd.DataFrame(table_data)
            st.dataframe(df, use_container_width=True)

            csv_file = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 تصدير السجلات كملف Excel / CSV", data=csv_file, file_name="database_export.csv", mime='text/csv', use_container_width=True)

    # 6. SCHEMA SETTINGS
    elif app_mode == "⚙️ إعدادات الحقول":
        st.subheader("⚙️ إعدادات وتخصيص حقول النموذج")

        with st.expander("➕ إضافة حقل جديد"):
            nf_name = st.text_input("اسم الحقل:")
            nf_type = st.selectbox("نوع الحقل:", ["نص (Text)", "رقم (Number)", "قائمة خيارات (Dropdown)", "تاريخ (Date)", "ملاحظات (Text Area)"])
            nf_opts = st.text_input("خيارات القائمة المنسدلة (فصل بالفاصلة):")
            nf_req = st.checkbox("حقل إجباري؟")

            if st.button("➕ حفظ الحقل", use_container_width=True):
                if not nf_name.strip():
                    st.error("يرجى إدخال اسم الحقل.")
                else:
                    conn = get_db()
                    conn.execute("INSERT INTO schema_fields (field_name, field_type, options, is_required) VALUES (?, ?, ?, ?)",
                                 (nf_name.strip(), nf_type, nf_opts.strip(), 1 if nf_req else 0))
                    conn.commit()
                    conn.close()
                    st.success("تم الحفظ بنجاح!")
                    st.rerun()

        st.divider()
        st.write("📋 الحقول الحالية:")
        for sf in schema_rows:
            c1, c2 = st.columns([4, 1])
            with c1:
                st.write(f"• **{sf['field_name']}** ({sf['field_type']})")
            with c2:
                if st.button("حذف 🗑️", key=f"delsf_{sf['id']}"):
                    conn = get_db()
                    conn.execute("DELETE FROM schema_fields WHERE id = ?", (sf['id'],))
                    conn.commit()
                    conn.close()
                    st.rerun()