import ssl
ssl._create_default_https_context = ssl._create_unverified_context

import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_autorefresh import st_autorefresh

# --- 1. ตั้งค่าพื้นฐาน (Page Config) ---
st.set_page_config(page_title="Hospital Smart Dashboard", page_icon="🏥", layout="wide")
st_autorefresh(interval=30000, key="auto_refresh")

# ==========================================
# ส่วนที่เพิ่มใหม่: HEADER & LOGO (ส่วนหัวแบบทางการ)
# ==========================================

# --- Sidebar: ตั้งค่าข้อมูลโรงพยาบาล ---
st.sidebar.title("⚙️ ตั้งค่าการแสดงผล")
st.sidebar.subheader("ข้อมูลองค์กร")

# 1. อัปโหลดโลโก้
uploaded_logo = st.sidebar.file_uploader("อัปโหลดโลโก้ รพ. (PNG/JPG)", type=['png', 'jpg', 'jpeg'])
# 2. ตั้งชื่อโรงพยาบาล
hospital_name = st.sidebar.text_input("ชื่อโรงพยาบาล/หน่วยงาน", value="โรงพยาบาลตัวอย่าง (Demo Hospital)")
sub_title = st.sidebar.text_input("ชื่อระบบ/แผนก", value="Smart Analytics Dashboard : ฝ่ายการพยาบาล")
# 3. ข้อมูลผู้จัดทำ
dev_name = st.sidebar.text_input("ชื่อผู้จัดทำ (Developer)", value="ทีมสารสนเทศทางการพยาบาล")

# --- แสดงผล Header บนหน้าจอหลัก ---
col_logo, col_header = st.columns([1, 5]) # แบ่งสัดส่วน โลโก้ 1 ส่วน : ข้อความ 5 ส่วน

with col_logo:
    if uploaded_logo is not None:
        st.image(uploaded_logo, width=120) # แสดงรูปที่อัปโหลด
    else:
        # แสดงรูปไอคอนพยาบาลตัวอย่าง ถ้ายังไม่ได้อัปโหลด
        st.markdown("## 🏥") 

with col_header:
    st.title(hospital_name) # ชื่อโรงพยาบาล (ตัวใหญ่)
    st.markdown(f"### {sub_title}") # ชื่อระบบ (ตัวรอง)

st.markdown("---") # เส้นขีดคั่นเพื่อความสวยงาม

# ==========================================
# ส่วนเดิม: การทำงานหลัก (Logic)
# ==========================================

# --- ส่วนเลือกแหล่งข้อมูล ---
st.subheader("📁 1. แหล่งข้อมูล (Data Source)")
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

# --- เริ่มการทำงานเมื่อมีข้อมูล ---
if df is not None:
    all_cols = df.columns.tolist()
    num_cols = df.select_dtypes(include=['float64', 'int64']).columns.tolist()
    cat_cols = df.select_dtypes(include=['object']).columns.tolist()
    time_keywords = ['date', 'time', 'year', 'month', 'day', 'วัน', 'เดือน', 'ปี']
    date_col = next((col for col in cat_cols if any(k in col.lower() for k in time_keywords)), None)

    # --- ส่วนกรองข้อมูล ---
    st.markdown("#### 🔍 2. กรองข้อมูล (Filter)")
    with st.container():
        c1, c2, c3 = st.columns([1, 1, 2])
        with c1: filter_main = st.selectbox("เลือกหัวข้อหลัก:", ["(แสดงทั้งหมด)"] + cat_cols)
        with c2:
            selected_sub = []
            if filter_main != "(แสดงทั้งหมด)":
                unique_val = df[filter_main].unique()
                selected_sub = st.multiselect(f"เลือก {filter_main}:", unique_val, default=unique_val)
            else: st.info("แสดงข้อมูลทั้งหมด")
        with c3: search_txt = st.text_input("ค้นหาเพิ่มเติม:", placeholder="พิมพ์คำที่ต้องการ...")

    df_filtered = df.copy()
    if filter_main != "(แสดงทั้งหมด)" and selected_sub:
        df_filtered = df_filtered[df_filtered[filter_main].isin(selected_sub)]
    if search_txt:
        mask = df_filtered.astype(str).apply(lambda x: x.str.contains(search_txt, case=False, na=False)).any(axis=1)
        df_filtered = df_filtered[mask]
    
    st.caption(f"⚡ แสดงผล: {len(df_filtered)} รายการ")

    # --- ส่วน Dashboard ---
    st.markdown("---")
    st.subheader("📈 3. สรุปผลภาพรวม (Dashboard)")

    if not df_filtered.empty:
        with st.expander("⚙️ ตั้งค่า KPI Card", expanded=True):
            selected_kpi_cols = st.multiselect("เลือกหัวข้อ KPI:", all_cols, default=all_cols[:4])

        if selected_kpi_cols:
            cols = st.columns(len(selected_kpi_cols))
            for i, col in enumerate(selected_kpi_cols):
                if col in num_cols:
                    val = df_filtered[col].sum()
                    cols[i].metric(label=f"ผลรวม {col}", value=f"{val:,.0f}")
                else:
                    count_total = len(df_filtered[col])
                    count_unique = df_filtered[col].nunique()
                    cols[i].metric(label=f"จำนวน {col}", value=f"{count_total:,}", delta=f"{count_unique} กลุ่มข้อมูล")

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

        with st.expander("📋 ตารางข้อมูลรายละเอียด", expanded=True):
            st.dataframe(df_filtered, use_container_width=True)
            csv = df_filtered.to_csv(index=False).encode('utf-8')
            st.download_button("⬇️ ดาวน์โหลด CSV", csv, "filtered_data.csv", "text/csv")
    else:
        st.warning("❌ ไม่พบข้อมูล")

else:
    st.info("👋 กรุณาเลือกวิธีนำเข้าข้อมูลด้านบน")

# ==========================================
# ส่วนที่เพิ่มใหม่: FOOTER (เครดิตผู้จัดทำ)
# ==========================================
st.markdown("<br><br>", unsafe_allow_html=True) # เว้นบรรทัด
st.markdown("---")
# จัดกึ่งกลาง และใส่สีเทาเพื่อให้ดูเป็น Footer
st.markdown(
    f"""
    <div style='text-align: center; color: grey;'>
        <p>Copyright © 2024 <b>{hospital_name}</b></p>
        <p>พัฒนาโดย: {dev_name} | Powered by Python Streamlit</p>
    </div>
    """, 
    unsafe_allow_html=True
)
