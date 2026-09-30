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
    page_title="منصة إدخال البيانات والذكاء الاصطناعي",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# 2. CUSTOM CSS STYLING (Modern RTL UI)
# ==========================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800&display=swap');

    html, body, [class*="css"], .stApp {
        font-family: 'Cairo', 'Segoe UI', Tahoma, sans-serif;
        background-color: #f8fafc;
        direction: rtl;
        text-align: right;
    }

    /* Keep Sidebar aligned right */
    section[data-testid="stSidebar"] {
        direction: rtl;
        text-align: right;
        background-color: #0f172a !important;
        color: #f8fafc;
    }
    
    section[data-testid="stSidebar"] * {
        color: #f8fafc !important;
    }

    /* Hero Banner */
    .app-hero {
        background: linear-gradient(135deg, #1e1b4b 0%, #312e81 50%, #4338ca 100%);
        color: white;
        padding: 30px;
        border-radius: 20px;
        box-shadow: 0 10px 25px rgba(49, 46, 129, 0.2);
        margin-bottom: 25px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 15px;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    .app-hero h1 {
        color: #ffffff !important;
        font-size: 26px;
        font-weight: 800;
        margin: 0;
    }
    .app-hero p {
        color: #c7d2fe;
        font-size: 14px;
        margin: 6px 0 0 0;
    }
    .user-badge {
        background: rgba(255, 255, 255, 0.12);
        padding: 8px 18px;
        border-radius: 30px;
        font-size: 13px;
        backdrop-filter: blur(8px);
        border: 1px solid rgba(255, 255, 255, 0.2);
    }

    /* Metric Cards */
    .metric-card {
        background: #ffffff;
        padding: 22px;
        border-radius: 16px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.03);
        border-right: 5px solid #4f46e5;
        border-top: 1px solid #f1f5f9;
        border-left: 1px solid #f1f5f9;
        border-bottom: 1px solid #f1f5f9;
        transition: all 0.3s ease;
    }
    .metric-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 25px rgba(0, 0, 0, 0.06);
    }
    .metric-title {
        font-size: 13px;
        color: #64748b;
        font-weight: 700;
    }
    .metric-value {
        font-size: 30px;
        font-weight: 800;
        color: #0f172a;
        margin-top: 6px;
    }

    /* AI Box Accent */
    .ai-box {
        background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%);
        border: 1px solid #86efac;
        padding: 20px;
        border-radius: 16px;
        margin-bottom: 20px;
    }

    /* Result & Record Cards */
    .record-card {
        background: #ffffff;
        border-radius: 14px;
        padding: 20px;
        margin-bottom: 15px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.03);
        border: 1px solid #e2e8f0;
        border-right: 5px solid #3b82f6;
    }
    .record-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 12px;
        border-bottom: 1px solid #f1f5f9;
        padding-bottom: 8px;
    }
    .record-title {
        font-size: 17px;
        font-weight: 700;
        color: #0f172a;
    }
    .record-badge {
        background: #e0f2fe;
        color: #0369a1;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 700;
    }

    /* Button Custom Styling */
    .stButton>button {
        border-radius: 10px;
        font-weight: 700;
        height: 45px;
        transition: all 0.2s ease;
    }

    /* Login Box */
    .login-container {
        max-width: 440px;
        margin: 40px auto 20px auto;
        background: #ffffff;
        padding: 35px;
        border-radius: 24px;
        box-shadow: 0 15px 35px rgba(0,0,0,0.06);
        text-align: center;
        border: 1px solid #e2e8f0;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 3. DATABASE SETUP & HELPER FUNCTIONS
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

    # Seed default fields if empty
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

    # Seed sample record if empty
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

# Rule-based Smart Extraction (AI Parsing Simulation)
def ai_extract_data(text_input, schema_fields):
    extracted = {}
    text = text_input.strip()
    
    # Extract phone numbers
    phone_match = re.search(r'05\d{8}|\+?\d{10,12}', text)
    # Extract amounts
    amount_match = re.search(r'(\d+)\s*(ريال|درهم|دولار|\$)?', text)

    for field in schema_fields:
        fname = field["field_name"]
        ftype = field["field_type"]

        if "هاتف" in fname or "تواصل" in fname or "رقم" in fname and ftype == "رقم (Number)":
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
            # Try getting first 2-3 words
            words = text.split()
            extracted[fname] = " ".join(words[:2]) if len(words) >= 2 else text
        else:
            extracted[fname] = text

    return extracted

# ==========================================
# 4. SESSION STATE MANAGEMENT
# ==========================================
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "user_email" not in st.session_state:
    st.session_state["user_email"] = ""
if "ai_prefilled" not in st.session_state:
    st.session_state["ai_prefilled"] = {}

# ==========================================
# 5. LOGIN SCREEN
# ==========================================
if not st.session_state["logged_in"]:
    st.markdown('''
    <div class="login-container">
        <div style="font-size: 55px; margin-bottom: 10px;">⚡</div>
        <h2 style="color: #1e1b4b; font-weight: 800; margin-bottom: 5px;">تطبيق إدخال البيانات الذكي</h2>
        <p style="color: #64748b; font-size: 14px; margin-bottom: 25px;">قم بتسجيل الدخول للوصول إلى قاعدة البيانات المتقدمة</p>
    </div>
    ''', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login_form"):
            email_input = st.text_input("📧 البريد الإلكتروني:", placeholder="name@example.com")
            password_input = st.text_input("🔑 كلمة المرور (اختياري):", type="password", placeholder="••••••••")
            submit_login = st.form_submit_button("🚀 دخول إلى المنصة", use_container_width=True)
            
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
# 6. MAIN APPLICATION INTERFACE
# ==========================================
else:
    # Header Banner
    st.markdown(f'''
    <div class="app-hero">
        <div>
            <h1>⚡ منصة إدارة البيانات والذكاء الاصطناعي</h1>
            <p>إدخال بيانات آلي، بحث فوري وتحليلات إحصائية متطورة</p>
        </div>
        <div class="user-badge">
            👤 المستخدم: <b>{st.session_state["user_email"]}</b>
        </div>
    </div>
    ''', unsafe_allow_html=True)

    # Sidebar Navigation
    with st.sidebar:
        st.markdown("### 📌 القائمة الرئيسية")
        app_mode = st.radio(
            "اختر الشاشة:",
            [
                "🏠 الرئيسية والإحصائيات",
                "🤖 المساعد الذكي (AI)",
                "📝 نموذج إدخال جديد",
                "🔍 البحث والتفتيش الفوري",
                "📊 قاعدة البيانات الكاملة",
                "⚙️ إعدادات الحقول"
            ],
            key="navigation_radio"
        )

        if "app_mode_override" in st.session_state:
            app_mode = st.session_state.pop("app_mode_override")

        st.divider()
        if st.button("🚪 تسجيل الخروج", use_container_width=True):
            st.session_state["logged_in"] = False
            st.session_state["user_email"] = ""
            st.rerun()

    # Get DB Metrics
    conn = get_db()
    total_records = conn.execute("SELECT COUNT(*) FROM records").fetchone()[0]
    total_fields = conn.execute("SELECT COUNT(*) FROM schema_fields").fetchone()[0]
    my_records = conn.execute("SELECT COUNT(*) FROM records WHERE user_email = ?", (st.session_state["user_email"],)).fetchone()[0]
    schema_rows = conn.execute("SELECT * FROM schema_fields").fetchall()
    conn.close()

    # ------------------------------------------
    # SCREEN 1: DASHBOARD
    # ------------------------------------------
    if app_mode == "🏠 الرئيسية والإحصائيات":
        st.subheader("📊 نظرة عامة على النظام")
        
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(f'''
            <div class="metric-card">
                <div class="metric-title">📁 إجمالي السجلات</div>
                <div class="metric-value">{total_records}</div>
            </div>
            ''', unsafe_allow_html=True)
        with c2:
            st.markdown(f'''
            <div class="metric-card" style="border-right-color: #10b981;">
                <div class="metric-title">👤 سجلاتك المدخلة</div>
                <div class="metric-value">{my_records}</div>
            </div>
            ''', unsafe_allow_html=True)
        with c3:
            st.markdown(f'''
            <div class="metric-card" style="border-right-color: #8b5cf6;">
                <div class="metric-title">⚙️ الحقول النشطة</div>
                <div class="metric-value">{total_fields}</div>
            </div>
            ''', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.subheader("⚡ الإجراءات السريعة")
        
        q1, q2, q3 = st.columns(3)
        with q1:
            if st.button("🤖 استخراج بيانات بالذكاء الاصطناعي", use_container_width=True):
                st.session_state["app_mode_override"] = "🤖 المساعد الذكي (AI)"
                st.rerun()
            st.caption("لصق نص واستخراج الحقول تلقائياً.")
        with q2:
            if st.button("📝 نموذج إدخال جديد", use_container_width=True):
                st.session_state["app_mode_override"] = "📝 نموذج إدخال جديد"
                st.rerun()
            st.caption("إضافة سجل يدوي مباشرة.")
        with q3:
            if st.button("🔍 البحث والتفتيش", use_container_width=True):
                st.session_state["app_mode_override"] = "🔍 البحث والتفتيش الفوري"
                st.rerun()
            st.caption("البحث الفوري وتعديل/حذف السجلات.")

    # ------------------------------------------
    # SCREEN 2: AI ASSISTANT
    # ------------------------------------------
    elif app_mode == "🤖 المساعد الذكي (AI)":
        st.subheader("🤖 أدوات الذكاء الاصطناعي والأتمتة")
        
        tab1, tab2 = st.tabs(["✨ استخراج البيانات الآلي من النصوص", "📈 التقرير والتحليل الذكي"])

        with tab1:
            st.markdown('''
            <div class="ai-box">
                <b>💡 كيف يعمل الاستخراج الذكي؟</b><br>
                قم بلصق أي رسالة عميل أو نص غير منظم (مثال: <i>"أنا عبدالله رقمي 0509876543 أريد طلب جديد بقيمة 3200 ريال"</i>)، وسيقوم الذكاء الاصطناعي بتفكيك النص وتعبئة النموذج فوراً!
            </div>
            ''', unsafe_allow_html=True)

            raw_text = st.text_area("✍️ ألصق النص هنا للتحليل والاستخراج:", height=120)
            
            if st.button("🪄 تحليل النص وتعبئة النموذج آلياً", use_container_width=True):
                if not raw_text.strip():
                    st.error("يرجى كتابة أو لصق نص أولاً.")
                else:
                    extracted_data = ai_extract_data(raw_text, schema_rows)
                    st.session_state["ai_prefilled"] = extracted_data
                    st.success("✅ تم تحليل النص بنجاح! تم نقل البيانات المستخرجة إلى شاشة '📝 نموذج إدخال جديد'.")
                    st.json(extracted_data)

        with tab2:
            st.subheader("📑 توليد تقرير تنفيذي ذكي")
            if st.button("⚡ إنشـاء التقرير الذكي الآن", use_container_width=True):
                conn = get_db()
                recs = conn.execute("SELECT data_json FROM records").fetchall()
                conn.close()

                if not recs:
                    st.info("لا توجد سجلات كافية لتحليلها.")
                else:
                    st.markdown("### 📝 ملخص التقرير الذكي:")
                    st.write(f"• **إجمالي المعاملات المسجلة:** {len(recs)} معاملة.")
                    st.write(f"• **معدل النشاط:** مرتفع ممتاز.")
                    st.write("• **التوصية الذكية:** يوصى بمتابعة الطلبات الجديدة وتحويل الحالات المعلقة لضمان سرعة الإنجاز.")

    # ------------------------------------------
    # SCREEN 3: FORM ENTRY
    # ------------------------------------------
    elif app_mode == "📝 نموذج إدخال جديد":
        st.subheader("📝 نموذج إدخال البيانات المطور")

        if st.session_state.get("ai_prefilled"):
            st.info("✨ تم تعبئة البيانات تلقائياً بواسطة الذكاء الاصطناعي. يمكنك مراجعتها وتعديلها قبل الحفظ.")

        if not schema_rows:
            st.warning("لم يتم تعيين أي حقول بعد. انتقل إلى '⚙️ إعدادات الحقول' لإضافة حقولك.")
        else:
            with st.form("web_data_form", clear_on_submit=True):
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

                btn_submit = st.form_submit_button("💾 حفظ البيانات في قاعدة البيانات", use_container_width=True)
                
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

    # ------------------------------------------
    # SCREEN 4: INSTANT SEARCH & ACTIONS
    # ------------------------------------------
    elif app_mode == "🔍 البحث والتفتيش الفوري":
        st.subheader("🔍 البحث الفوري والتعديل")

        search_query = st.text_input("🔎 ابحث باسم العميل، الهاتف، أو الكلمات المفتاحية:", placeholder="اكتب للبحث...")
        
        conn = get_db()
        all_recs = conn.execute("SELECT * FROM records ORDER BY id DESC").fetchall()
        conn.close()

        filtered_recs = []
        for r in all_recs:
            data_dict = json.loads(r["data_json"])
            full_text = f"{r['id']} {r['user_email']} {r['created_at']} " + " ".join([str(v) for v in data_dict.values()])
            if search_query.strip() == "" or search_query.strip().lower() in full_text.lower():
                filtered_recs.append((r, data_dict))

        st.write(f"🔍 النتائج المطلوبة: **{len(filtered_recs)}** سجل")
        
        if not filtered_recs:
            st.warning("لا توجد نتائج مطابقة.")
        else:
            for r, ddict in filtered_recs:
                first_key = list(ddict.keys())[0] if ddict else "سجل"
                first_val = ddict.get(first_key, "بدون عنوان")
                
                st.markdown(f'''
                <div class="record-card">
                    <div class="record-header">
                        <span class="record-title">📌 #{r["id"]} - {first_val}</span>
                        <span class="record-badge">بواسطة: {r["user_email"]} | {r["created_at"][:10]}</span>
                    </div>
                </div>
                ''', unsafe_allow_html=True)
                
                cols = st.columns(2)
                idx = 0
                for k, v in ddict.items():
                    with cols[idx % 2]:
                        st.write(f"• **{k}**: {v}")
                    idx += 1

                # Actions: Delete
                btn_del = st.button(f"🗑️ حذف السجل #{r['id']}", key=f"del_rec_{r['id']}")
                if btn_del:
                    conn = get_db()
                    conn.execute("DELETE FROM records WHERE id = ?", (r['id'],))
                    conn.commit()
                    conn.close()
                    st.success(f"تم حذف السجل #{r['id']}")
                    st.rerun()

                st.divider()

    # ------------------------------------------
    # SCREEN 5: DATABASE VIEW & EXPORT
    # ------------------------------------------
    elif app_mode == "📊 قاعدة البيانات الكاملة":
        st.subheader("📊 استعراض وتصدير قاعدة البيانات")
        
        conn = get_db()
        recs = conn.execute("SELECT id, user_email, created_at, data_json FROM records ORDER BY id DESC").fetchall()
        conn.close()

        if not recs:
            st.info("لا توجد بيانات مسجلة حالياً.")
        else:
            table_data = []
            for r in recs:
                row_dict = {
                    "رقم السجل": r["id"],
                    "المُدخل": r["user_email"],
                    "التاريخ": r["created_at"]
                }
                row_dict.update(json.loads(r["data_json"]))
                table_data.append(row_dict)

            df = pd.DataFrame(table_data)
            st.dataframe(df, use_container_width=True)

            csv_file = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label="📥 تصدير السجلات كملف Excel / CSV",
                data=csv_file,
                file_name=f"database_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime='text/csv',
                use_container_width=True
            )

    # ------------------------------------------
    # SCREEN 6: SCHEMA MANAGEMENT
    # ------------------------------------------
    elif app_mode == "⚙️ إعدادات الحقول":
        st.subheader("⚙️ تخصيص حقول النموذج")

        with st.expander("➕ إضافة حقل جديد", expanded=True):
            nf_name = st.text_input("اسم الحقل الجديد:")
            nf_type = st.selectbox("نوع الحقل:", ["نص (Text)", "رقم (Number)", "قائمة خيارات (Dropdown)", "تاريخ (Date)", "ملاحظات (Text Area)"])
            nf_opts = st.text_input("خيارات القائمة المنسدلة (فصل بالفاصلة):", placeholder="جديد, قيد التنفيذ, مكتمل")
            nf_req = st.checkbox("حقل إجباري؟")

            if st.button("➕ حفظ وإضافة الحقل", use_container_width=True):
                if not nf_name.strip():
                    st.error("يرجى إدخال اسم الحقل.")
                else:
                    conn = get_db()
                    conn.execute("INSERT INTO schema_fields (field_name, field_type, options, is_required) VALUES (?, ?, ?, ?)",
                                 (nf_name.strip(), nf_type, nf_opts.strip(), 1 if nf_req else 0))
                    conn.commit()
                    conn.close()
                    st.success(f"تمت إضافة الحقل '{nf_name}' بنجاح!")
                    st.rerun()

        st.divider()
        st.write("📋 الحقول الحالية:")
        for sf in schema_rows:
            c1, c2 = st.columns([4, 1])
            with c1:
                req_badge = " [إجباري]" if sf["is_required"] else ""
                st.write(f"• **{sf['field_name']}** ({sf['field_type']}){req_badge}")
            with c2:
                if st.button("حذف 🗑️", key=f"del_sf_{sf['id']}"):
                    conn = get_db()
                    conn.execute("DELETE FROM schema_fields WHERE id = ?", (sf['id'],))
                    conn.commit()
                    conn.close()
                    st.success("تم الحذف.")
                    st.rerun()