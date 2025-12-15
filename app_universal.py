import ssl
# แก้ปัญหา Certificate สำหรับเครื่องบางเครื่อง
ssl._create_default_https_context = ssl._create_unverified_context

import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_autorefresh import st_autorefresh

# ==========================================
# ⚙️ ส่วนตั้งค่า (แก้ไขข้อความตรงนี้)
# ==========================================
LOGO_FILENAME = "logo.png"  # ชื่อไฟล์โลโก้ (ต้องวางคู่กับไฟล์ app.py)
HOSPITAL_NAME = "โรงพยาบาลราชวิถี"
SYSTEM_NAME = "Smart Analytics Dashboard : งานถ่ายทอดการพยาบาล"
DEV_NAME = "งานถ่ายทอดการพยาบาล"

# ==========================================
# 1. ตั้งค่าหน้าเว็บ
# ==========================================
st.set_page_config(page_title=SYSTEM_NAME, page_icon="🏥", layout="wide")
st_autorefresh(interval=30000, key="auto_refresh")

# ==========================================
# 2. ส่วนหัว (HEADER) - แบบ Hardcode
# ==========================================
c_logo, c_title = st.columns([1, 6])

with c_logo:
    try:
        st.image(LOGO_FILENAME, width=110)
    except:
        # ถ้าหาไฟล์รูปไม่เจอ ให้โชว์ไอคอนแทน
        st.markdown("# 🏥")

with c_title:
    st.title(HOSPITAL_NAME)
    st.markdown(f"### {SYSTEM_NAME}")

st.markdown("---")

# ==========================================
# 3. ส่วนนำเข้าข้อมูล (Data Source)
# ==========================================
st.subheader("📁 1. แหล่งข้อมูล")
tab_excel, tab_gsheet = st.tabs(["📂 อัปโหลด Excel", "🔗 ลิงก์ Google Sheets"])
df = None 

# TAB 1: Excel
with tab_excel:
    uploaded_file = st.file_uploader("เลือกไฟล์ Excel (.xlsx)", type=["xlsx", "xls"])
    if uploaded_file is not None:
        try:
            df = pd.read_excel(uploaded_file)
            st.success(f"✅ โหลดไฟล์สำเร็จ: {uploaded_file.name}")
        except Exception as e:
            st.error(f"❌ อ่านไฟล์ไม่ได้: {e}")

# TAB 2: Google Sheets
with tab_gsheet:
    default_url = "https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/edit?usp=sharing"
    gsheet_url = st.text_input("วางลิงก์ Google Sheet:", value=default_url)

    @st.cache_data(ttl=0)
    def load_gsheet_data(url):
        try:
            if "docs.google.com/spreadsheets" in url:
                export_url = url.replace('/edit?usp=sharing', '/export?format=csv').replace('/edit', '/export?format=csv')
                if "#gid=" in url:
                    gid_part = url.split("#gid=")[1]
                    export_url = f"{export_url}&gid={gid_part}"
                return pd.read_csv(export_url)
            return None
        except Exception as e:
            st.error(f"❌ อ่าน Link ไม่ได้: {e}")
            return None

    if df is None and gsheet_url:
        df_gs = load_gsheet_data(gsheet_url)
        if df_gs is not None:
            df = df_gs
            st.success("✅ เชื่อมต่อ Google Sheet สำเร็จ")

# ==========================================
# 4. เริ่มประมวลผล (เมื่อมีข้อมูล)
# ==========================================
if df is not None:
    all_cols = df.columns.tolist()
    num_cols = df.select_dtypes(include=['float64', 'int64']).columns.tolist()
    cat_cols = df.select_dtypes(include=['object']).columns.tolist()
    time_keywords = ['date', 'time', 'year', 'month', 'day', 'วัน', 'เดือน', 'ปี']
    date_col = next((col for col in cat_cols if any(k in col.lower() for k in time_keywords)), None)

    # --- ส่วนกรองข้อมูล (Filter) ---
    st.markdown("#### 🔍 2. กรองข้อมูล (Filter)")
    # ใช้ style container เพื่อความสวยงาม
    with st.container():
        c1, c2, c3 = st.columns([1, 1, 2])
        with c1: filter_main = st.selectbox("เลือกหัวข้อหลัก:", ["(แสดงทั้งหมด)"] + cat_cols)
        with c2:
            selected_sub = []
            if filter_main != "(แสดงทั้งหมด)":
                unique_val = df[filter_main].unique()
                selected_sub = st.multiselect(f"เลือก {filter_main}:", unique_val, default=unique_val)
            else: st.info("แสดงข้อมูลทั้งหมด")
        with c3: search_txt = st.text_input("ค้นหาเพิ่มเติม:", placeholder="พิมพ์คำค้นหา...")

    # Logic การกรอง
    df_filtered = df.copy()
    if filter_main != "(แสดงทั้งหมด)" and selected_sub:
        df_filtered = df_filtered[df_filtered[filter_main].isin(selected_sub)]
    if search_txt:
        mask = df_filtered.astype(str).apply(lambda x: x.str.contains(search_txt, case=False, na=False)).any(axis=1)
        df_filtered = df_filtered[mask]
    
    st.caption(f"⚡ แสดงผล: {len(df_filtered)} รายการ")

    # --- ส่วน Dashboard ---
    st.markdown("---")
    st.subheader("📈 3. สรุปผลภาพรวม")

    if not df_filtered.empty:
        # เลือก KPI (ใส่ไว้ใน Expander เพื่อไม่ให้รก)
        with st.expander("⚙️ เลือกหัวข้อ KPI Card", expanded=True):
            selected_kpi_cols = st.multiselect("เลือกข้อมูลที่จะสรุปยอด:", all_cols, default=all_cols[:4])

        if selected_kpi_cols:
            cols = st.columns(len(selected_kpi_cols))
            for i, col in enumerate(selected_kpi_cols):
                if col in num_cols:
                    val = df_filtered[col].sum()
                    cols[i].metric(label=f"ผลรวม {col}", value=f"{val:,.0f}")
                else:
                    count_total = len(df_filtered[col])
                    count_unique = df_filtered[col].nunique()
                    cols[i].metric(label=f"จำนวน {col}", value=f"{count_total:,}", delta=f"{count_unique} กลุ่ม")

        # กราฟ
        st.markdown("---")
        g1, g2 = st.columns([2, 1])
        with g1:
            if date_col and num_cols:
                y_axis = st.selectbox("แกน Y (กราฟเส้น):", num_cols, key="g1_y")
                fig = px.line(df_filtered, x=date_col, y=y_axis, markers=True, title=f"Trend: {y_axis}")
            elif cat_cols:
                x_axis = st.selectbox("แกน X (กราฟแท่ง):", cat_cols, index=0, key="g1_x")
                if num_cols:
                    y_axis = st.selectbox("ค่าแกน Y:", num_cols, index=0, key="g1_y_bar")
                    fig = px.bar(df_filtered, x=x_axis, y=y_axis, color=x_axis, title=f"ผลรวม {y_axis} ตาม {x_axis}")
                else:
                    fig = px.histogram(df_filtered, x=x_axis, title=f"จำนวนรายการแยกตาม {x_axis}")
            if fig: st.plotly_chart(fig, use_container_width=True)

        with g2:
            if cat_cols:
                pie_col = st.selectbox("กราฟวงกลม:", cat_cols, index=min(1, len(cat_cols)-1), key="g2_pie")
                if num_cols:
                    fig_pie = px.pie(df_filtered, values=num_cols[0], names=pie_col, title=f"สัดส่วน {num_cols[0]}")
                else:
                    fig_pie = px.pie(df_filtered, names=pie_col, title=f"สัดส่วนจำนวน {pie_col}")
                st.plotly_chart(fig_pie, use_container_width=True)

        # ตาราง
        with st.expander("📋 ดูตารางข้อมูลรายละเอียด", expanded=True):
            st.dataframe(df_filtered, use_container_width=True)
            csv = df_filtered.to_csv(index=False).encode('utf-8')
            st.download_button("⬇️ ดาวน์โหลด CSV", csv, "filtered_data.csv", "text/csv")
    else:
        st.warning("❌ ไม่พบข้อมูลตามเงื่อนไข")

else:
    st.info("👋 กรุณาเลือกวิธีนำเข้าข้อมูลด้านบน")

# ==========================================
# 5. FOOTER (เครดิตผู้จัดทำ)
# ==========================================
st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown("---")
st.markdown(
    f"""
    <div style='text-align: center; color: grey;'>
        <p>Copyright © 2024 <b>งานถ่ายทอดการพยาบาล โรงพยาบาลราชวิถี</b></p>
        <p>พัฒนาโดย: Nattachai Russmeedara | Powered by Python Streamlit</p>
    </div>
    """, 
    unsafe_allow_html=True
)
