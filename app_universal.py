import ssl
ssl._create_default_https_context = ssl._create_unverified_context

import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_autorefresh import st_autorefresh

# ==========================================
# ⚙️ ส่วนตั้งค่า (แก้ไขข้อความตรงนี้)
# ==========================================
LOGO_FILENAME = "logo.png"
HOSPITAL_NAME = "โรงพยาบาลราชวิถี (Rajavithi Hospital)"
SYSTEM_NAME = "Smart Analytics Dashboard : งานถ่ายทอดการพยาบาล"
DEV_NAME = "งานถ่ายทอดการพยาบาล"

# ==========================================
# 1. ตั้งค่าหน้าเว็บ
# ==========================================
st.set_page_config(page_title=SYSTEM_NAME, page_icon="🏥", layout="wide")
st_autorefresh(interval=30000, key="auto_refresh")

# ==========================================
# 2. ส่วนหัว (HEADER)
# ==========================================
c_logo, c_title = st.columns([1, 6])
with c_logo:
    try:
        st.image(LOGO_FILENAME, width=110)
    except:
        st.markdown("# 🏥")
with c_title:
    st.title(HOSPITAL_NAME)
    st.markdown(f"### {SYSTEM_NAME}")
st.markdown("---")

# ==========================================
# 3. นำเข้าข้อมูล
# ==========================================
st.subheader("📁 1. แหล่งข้อมูล")
tab_excel, tab_gsheet = st.tabs(["📂 อัปโหลด Excel", "🔗 ลิงก์ Google Sheets"])
df = None 

with tab_excel:
    uploaded_file = st.file_uploader("เลือกไฟล์ Excel (.xlsx)", type=["xlsx", "xls"])
    if uploaded_file is not None:
        try:
            df = pd.read_excel(uploaded_file)
            st.success(f"✅ โหลดไฟล์สำเร็จ: {uploaded_file.name}")
        except Exception as e:
            st.error(f"❌ อ่านไฟล์ไม่ได้: {e}")

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
# 4. ประมวลผลและแสดงผล
# ==========================================
if df is not None:
    all_cols = df.columns.tolist()
    num_cols = df.select_dtypes(include=['float64', 'int64']).columns.tolist()
    cat_cols = df.select_dtypes(include=['object']).columns.tolist()
    
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
        with c3: search_txt = st.text_input("ค้นหาเพิ่มเติม:", placeholder="พิมพ์คำค้นหา...")

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
        # KPI Cards
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
                    cols[i].metric(label=f"จำนวน {col}", value=f"{count_total:,} รายการ")

        st.markdown("---")
        
        # กราฟ Stacked Bar & Pie
        g1, g2 = st.columns([2, 1])
        
        with g1:
            st.markdown("##### 📊 กราฟแท่ง (Bar Chart)")
            x_axis = st.selectbox("แกน X (แนวนอน):", cat_cols, index=0, key="bar_x")
            y_options = ["(นับจำนวนรายการ)"] + num_cols
            y_axis = st.selectbox("แกน Y (แนวตั้ง):", y_options, key="bar_y")
            stack_col = st.selectbox("แบ่งกลุ่มย่อย (ซ้อนกัน/สี):", ["(ไม่มี)"] + cat_cols, key="bar_stack")
            
            color_var = stack_col if stack_col != "(ไม่มี)" else x_axis
            
            if y_axis == "(นับจำนวนรายการ)":
                fig_main = px.histogram(df_filtered, x=x_axis, color=color_var, barmode='stack', text_auto=True)
            else:
                fig_main = px.histogram(df_filtered, x=x_axis, y=y_axis, color=color_var, barmode='stack', text_auto=True)
            
            st.plotly_chart(fig_main, use_container_width=True)

        with g2:
            st.markdown("##### 🍰 กราฟวงกลม (Pie Chart)")
            if cat_cols:
                pie_col = st.selectbox("หัวข้อกราฟวงกลม:", cat_cols, index=min(1, len(cat_cols)-1), key="pie_select")
                pie_val_opt = st.selectbox("ค่าที่แสดง:", ["(นับจำนวน)"] + num_cols, key="pie_val")
                
                if pie_val_opt == "(นับจำนวน)":
                    fig_pie = px.pie(df_filtered, names=pie_col, hole=0.4)
                else:
                    fig_pie = px.pie(df_filtered, values=pie_val_opt, names=pie_col, hole=0.4)
                
                st.plotly_chart(fig_pie, use_container_width=True)

        # ========================================================
        # 📝 ส่วนเพิ่มใหม่: Text Viewer (สำหรับอ่านข้อความ)
        # ========================================================
        st.markdown("---")
        st.subheader("📝 4. อ่านข้อความ/ข้อเสนอแนะ (Text Comments)")
        
        with st.container():
            # ให้เลือกคอลัมน์ที่เป็นข้อความ
            text_col_select = st.selectbox("เลือกคอลัมน์ข้อความที่ต้องการอ่าน:", cat_cols, index=len(cat_cols)-1)
            
            # ดึงข้อมูลเฉพาะคอลัมน์นั้น ที่ไม่เป็นค่าว่าง (NaN)
            text_data = df_filtered[text_col_select].dropna().astype(str)
            text_data = text_data[text_data != "nan"] # กรองคำว่า nan ออก
            text_data = text_data[text_data != ""]    # กรองค่าว่างออก

            if not text_data.empty:
                st.caption(f"พบข้อความทั้งหมด {len(text_data)} รายการ")
                
                # สร้างกล่องข้อความแบบ Scroll ได้
                with st.container(height=400): # กำหนดความสูงกล่อง (เลื่อนดูได้)
                    for i, txt in enumerate(text_data):
                        # แสดงเป็นการ์ดข้อความสวยๆ
                        st.info(f"💬 {txt}")
            else:
                st.warning("ไม่มีข้อความในคอลัมน์นี้ หรือข้อมูลว่างเปล่า")

        # ตารางข้อมูลดิบ
        st.markdown("---")
        with st.expander("📋 ดูตารางข้อมูลทั้งหมด", expanded=False):
            st.dataframe(df_filtered, use_container_width=True)
            csv = df_filtered.to_csv(index=False).encode('utf-8')
            st.download_button("⬇️ ดาวน์โหลด CSV", csv, "filtered_data.csv", "text/csv")

    else:
        st.warning("❌ ไม่พบข้อมูลตามเงื่อนไข")

else:
    st.info("👋 กรุณาเลือกวิธีนำเข้าข้อมูลด้านบน")

# FOOTER
st.markdown("<br><br><hr>", unsafe_allow_html=True)
st.markdown(f"<div style='text-align: center; color: grey;'><p>Copyright © 2025 <b>งานถ่ายทอดการพยาบาล โรงพยาบาลราชวิถี</b></p><p>พัฒนาโดย: Nattachai Russmeedara</p></div>", unsafe_allow_html=True)
