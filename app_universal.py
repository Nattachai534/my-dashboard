import ssl
# แก้ปัญหา Certificate ในเครื่อง Mac/Windows
ssl._create_default_https_context = ssl._create_unverified_context

import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_autorefresh import st_autorefresh

# --- 1. ตั้งค่าพื้นฐาน ---
st.set_page_config(page_title="Smart Analytics Dashboard", page_icon="📊", layout="wide")
st_autorefresh(interval=30000, key="auto_refresh")

st.title("📊 Smart Analytics Dashboard")
st.markdown("ระบบวิเคราะห์ข้อมูลที่เชื่อมโยงกันทั้งระบบ (KPIs, กราฟ, ตาราง)")

# --- 2. ส่วนเลือกแหล่งข้อมูล (Dual Input) ---
st.markdown("---")
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
    # เตรียมข้อมูลคอลัมน์
    all_cols = df.columns.tolist()
    num_cols = df.select_dtypes(include=['float64', 'int64']).columns.tolist() # ตัวเลข
    cat_cols = df.select_dtypes(include=['object']).columns.tolist() # ตัวหนังสือ
    
    # หาคอลัมน์วันที่
    time_keywords = ['date', 'time', 'year', 'month', 'day', 'วัน', 'เดือน', 'ปี']
    date_col = next((col for col in cat_cols if any(k in col.lower() for k in time_keywords)), None)

    # ==========================================
    # ส่วนที่ 3: ตัวกรอง (Filter) - หัวใจสำคัญ
    # ==========================================
    st.markdown("---")
    st.subheader("🔍 2. กรองข้อมูล (Filter)")
    
    # ใช้กรอบสีฟ้าครอบส่วนกรองเพื่อให้เด่นชัด
    with st.container():
        c1, c2, c3 = st.columns([1, 1, 2])
        
        # 3.1 เลือกหัวข้อกรอง
        with c1:
            filter_main = st.selectbox("เลือกหัวข้อหลัก:", ["(แสดงทั้งหมด)"] + cat_cols)
        
        # 3.2 เลือกค่าในหัวข้อ
        with c2:
            selected_sub = []
            if filter_main != "(แสดงทั้งหมด)":
                unique_val = df[filter_main].unique()
                selected_sub = st.multiselect(f"เลือก {filter_main}:", unique_val, default=unique_val)
            else:
                st.info("แสดงข้อมูลทั้งหมด")

        # 3.3 ค้นหาอิสระ
        with c3:
            search_txt = st.text_input("ค้นหาเพิ่มเติม (พิมพ์คำที่ต้องการ):", placeholder="เช่น ชื่อคน, จังหวัด...")

    # --- PROCESS FILTER (กรองข้อมูลจริง) ---
    df_filtered = df.copy()

    # กรองชั้นที่ 1 (Dropdown)
    if filter_main != "(แสดงทั้งหมด)" and selected_sub:
        df_filtered = df_filtered[df_filtered[filter_main].isin(selected_sub)]
    
    # กรองชั้นที่ 2 (Search Text)
    if search_txt:
        mask = df_filtered.astype(str).apply(lambda x: x.str.contains(search_txt, case=False, na=False)).any(axis=1)
        df_filtered = df_filtered[mask]

    st.caption(f"⚡ ข้อมูลที่แสดงผล: {len(df_filtered)} รายการ (จากทั้งหมด {len(df)})")

    # ==========================================
    # ส่วนที่ 4: สรุปผล KPI (ปรับปรุงใหม่ตามโจทย์)
    # ==========================================
    st.markdown("---")
    st.subheader("📈 3. สรุปผลภาพรวม (Dashboard)")

    if not df_filtered.empty:
        # ให้ User เลือกได้เองว่าจะโชว์ KPI อะไรบ้าง
        with st.expander("⚙️ ตั้งค่า: เลือกข้อมูลที่จะแสดงใน KPI Card", expanded=True):
            # Default: เลือกคอลัมน์ทั้งหมดมาให้เลือก
            selected_kpi_cols = st.multiselect("เลือกหัวข้อที่ต้องการสรุปยอด (เลือกได้หลายอัน):", all_cols, default=all_cols[:4])

        # แสดง KPI Cards
        if selected_kpi_cols:
            # จัดแถว KPI (4 การ์ดต่อ 1 แถว)
            cols = st.columns(len(selected_kpi_cols))
            
            for i, col in enumerate(selected_kpi_cols):
                # ตรวจสอบว่าเป็น "ตัวเลข" หรือ "ตัวหนังสือ"
                if col in num_cols:
                    # ถ้าเป็นตัวเลข -> รวมผล (Sum)
                    val = df_filtered[col].sum()
                    cols[i].metric(label=f"ผลรวม {col}", value=f"{val:,.0f}")
                else:
                    # ถ้าเป็นตัวหนังสือ -> นับจำนวน (Count)
                    # นับจำนวนรายการทั้งหมด
                    count_total = len(df_filtered[col])
                    # นับจำนวนที่ไม่ซ้ำ (เช่น มี 5 จังหวัด)
                    count_unique = df_filtered[col].nunique()
                    
                    cols[i].metric(label=f"จำนวน {col}", value=f"{count_total:,}", delta=f"{count_unique} รายการไม่ซ้ำ")
        else:
            st.info("กรุณาเลือกหัวข้อ KPI ด้านบน ☝️")

        st.markdown("---")

        # ==========================================
        # ส่วนที่ 5: กราฟ (Linked Graphs)
        # ==========================================
        g1, g2 = st.columns([2, 1])
        
        with g1:
            if date_col and num_cols:
                y_axis = st.selectbox("แกน Y (แนวโน้ม):", num_cols, key="g1_y")
                fig = px.line(df_filtered, x=date_col, y=y_axis, markers=True, title=f"Trend: {y_axis}")
            elif cat_cols:
                # ถ้าไม่มีวันที่ ให้กราฟแท่งนับจำนวนตามหมวดหมู่
                x_axis = st.selectbox("เลือกแกน X (กราฟแท่ง):", cat_cols, index=0, key="g1_x")
                if num_cols:
                    y_axis = st.selectbox("เลือกค่าที่จะรวม (แกน Y):", num_cols, index=0, key="g1_y_bar")
                    fig = px.bar(df_filtered, x=x_axis, y=y_axis, color=x_axis, title=f"ผลรวม {y_axis} แยกตาม {x_axis}")
                else:
                    # นับจำนวนเฉยๆ
                    fig = px.histogram(df_filtered, x=x_axis, title=f"จำนวนรายการแยกตาม {x_axis}")
            
            if fig: st.plotly_chart(fig, use_container_width=True)

        with g2:
            if cat_cols:
                pie_col = st.selectbox("เลือกหัวข้อกราฟวงกลม:", cat_cols, index=min(1, len(cat_cols)-1), key="g2_pie")
                if num_cols:
                    # วงกลมแบบมีค่าตัวเลข
                    fig_pie = px.pie(df_filtered, values=num_cols[0], names=pie_col, title=f"สัดส่วน {num_cols[0]}")
                else:
                    # วงกลมแบบนับจำนวน
                    fig_pie = px.pie(df_filtered, names=pie_col, title=f"สัดส่วนจำนวนตาม {pie_col}")
                st.plotly_chart(fig_pie, use_container_width=True)

        # ==========================================
        # ส่วนที่ 6: ตารางข้อมูล (Filtered Table)
        # ==========================================
        st.markdown("---")
        with st.expander("📋 ตารางข้อมูลรายละเอียด (คลิกเพื่อดู)", expanded=True):
            st.dataframe(df_filtered, use_container_width=True)
            csv = df_filtered.to_csv(index=False).encode('utf-8')
            st.download_button("⬇️ ดาวน์โหลดข้อมูลที่กรอง (CSV)", csv, "filtered_data.csv", "text/csv")
            
    else:
        st.warning("❌ ไม่พบข้อมูลที่ตรงกับเงื่อนไขการกรอง")

else:
    st.info("👋 กรุณาเลือกวิธีนำเข้าข้อมูลด้านบนเพื่อเริ่มต้น")
