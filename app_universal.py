import ssl
# แก้ปัญหา Certificate ในเครื่อง Mac (ตามที่คุณทำไว้)
ssl._create_default_https_context = ssl._create_unverified_context

import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_autorefresh import st_autorefresh

# --- 1. ตั้งค่าพื้นฐาน ---
st.set_page_config(page_title="Universal Dashboard Pro", page_icon="📊", layout="wide")

# ตั้งค่า Refresh อัตโนมัติทุก 30 วินาที
st_autorefresh(interval=30000, key="auto_refresh")

st.title("📊 Universal Smart Dashboard (Pro)")
st.markdown("รองรับทั้งไฟล์ Excel และ Google Sheets พร้อมระบบกรองข้อมูลที่แม่นยำ")

# --- 2. ส่วนเลือกแหล่งข้อมูล (Dual Input System) ---
st.markdown("---")
st.subheader("📁 1. เลือกแหล่งข้อมูล")

# สร้าง Tab สำหรับเลือกวิธีนำเข้าข้อมูล
tab_excel, tab_gsheet = st.tabs(["📂 อัปโหลดไฟล์ Excel", "🔗 ลิงก์ Google Sheets"])

df = None  # ตัวแปรสำหรับเก็บข้อมูลที่จะนำไปใช้ต่อ

# === TAB 1: สำหรับไฟล์ Excel ===
with tab_excel:
    uploaded_file = st.file_uploader("เลือกไฟล์ Excel (.xlsx) จากเครื่องของคุณ", type=["xlsx", "xls"])
    if uploaded_file is not None:
        try:
            df = pd.read_excel(uploaded_file)
            st.success(f"✅ อ่านไฟล์ Excel สำเร็จ: {uploaded_file.name}")
        except Exception as e:
            st.error(f"❌ อ่านไฟล์ไม่ได้: {e}")

# === TAB 2: สำหรับ Google Sheets (ใช้ฟังก์ชันเดิมของคุณ) ===
with tab_gsheet:
    # Link เริ่มต้น
    default_url = "https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/edit?usp=sharing"
    gsheet_url = st.text_input("วางลิงก์ Google Sheet ที่นี่:", value=default_url)

    @st.cache_data(ttl=0)
    def load_gsheet_data(url):
        try:
            if "docs.google.com/spreadsheets" in url:
                # แปลง Link
                export_url = url.replace('/edit?usp=sharing', '/export?format=csv').replace('/edit', '/export?format=csv')
                # จัดการ gid
                if "#gid=" in url:
                    gid_part = url.split("#gid=")[1]
                    export_url = f"{export_url}&gid={gid_part}"
                
                return pd.read_csv(export_url)
            return None
        except Exception as e:
            st.error(f"❌ อ่านไฟล์ Google Sheet ไม่ได้: {e}")
            return None

    # ถ้าไม่ได้อัป Excel ให้ลองดูที่ Google Sheet
    if df is None and gsheet_url:
        df_gs = load_gsheet_data(gsheet_url)
        if df_gs is not None:
            df = df_gs
            st.success("✅ เชื่อมต่อ Google Sheet สำเร็จ")

# --- 3. เริ่มทำงานเมื่อมีข้อมูล (df) ---
if df is not None:
    # เตรียมข้อมูลคอลัมน์
    all_cols = df.columns.tolist()
    num_cols = df.select_dtypes(include=['float64', 'int64']).columns.tolist()
    cat_cols = df.select_dtypes(include=['object']).columns.tolist()
    
    # หาคอลัมน์วันที่อัตโนมัติ
    time_keywords = ['date', 'time', 'year', 'month', 'day', 'วัน', 'เดือน', 'ปี', 'เวลา']
    date_col = next((col for col in cat_cols if any(k in col.lower() for k in time_keywords)), None)

    # ==========================================
    # ส่วนที่ 4: ระบบกรองข้อมูล (Filter)
    # ==========================================
    st.markdown("---")
    st.subheader("🔍 2. กรองและค้นหาข้อมูล")

    # จัดวาง Layout ตัวกรอง
    c_filter1, c_filter2, c_search = st.columns([1, 1, 2])

    with c_filter1:
        # เลือกหัวข้อที่จะกรอง
        filter_col = st.selectbox("กรองด้วยหัวข้อ:", ["(แสดงทั้งหมด)"] + cat_cols)

    with c_filter2:
        # เลือกค่าในหัวข้อนั้น
        if filter_col != "(แสดงทั้งหมด)":
            unique_vals = df[filter_col].unique()
            selected_vals = st.multiselect(f"เลือก {filter_col}:", unique_vals, default=unique_vals)
        else:
            selected_vals = []
            st.info("แสดงข้อมูลทั้งหมด")

    with c_search:
        # ช่องค้นหาอิสระ
        search_query = st.text_input("พิมพ์คำค้นหาเพิ่มเติม (Search):", placeholder="เช่น ชื่อคน, รหัส, แผนก...")

    # --- PROCESS FILTERING (กรองข้อมูลจริง) ---
    df_filtered = df.copy()

    # 1. กรองตาม Dropdown
    if filter_col != "(แสดงทั้งหมด)" and selected_vals:
        df_filtered = df_filtered[df_filtered[filter_col].isin(selected_vals)]
    
    # 2. กรองตามคำค้นหา (Search Box)
    if search_query:
        mask = df_filtered.astype(str).apply(lambda x: x.str.contains(search_query, case=False, na=False)).any(axis=1)
        df_filtered = df_filtered[mask]

    # แสดงผลจำนวนที่พบ
    st.caption(f"⚡ ผลลัพธ์: พบ {len(df_filtered)} รายการ (จากทั้งหมด {len(df)})")

    # ==========================================
    # ส่วนที่ 5: แสดงตารางข้อมูล (Data Table)
    # ==========================================
    # ใส่ใน Expander เพื่อไม่ให้รก และแสดงเฉพาะข้อมูลที่กรองมาแล้วเท่านั้น
    with st.expander("📋 ดูตารางข้อมูลรายละเอียด (คลิกเพื่อดู)", expanded=True):
        if not df_filtered.empty:
            st.dataframe(df_filtered, use_container_width=True, height=350)
            
            # ปุ่มดาวน์โหลด
            csv = df_filtered.to_csv(index=False).encode('utf-8')
            st.download_button("⬇️ ดาวน์โหลดข้อมูลชุดนี้ (CSV)", csv, "filtered_data.csv", "text/csv")
        else:
            st.warning("❌ ไม่พบข้อมูลที่ตรงกับเงื่อนไข")

    # ==========================================
    # ส่วนที่ 6: แสดง Dashboard & Graphs
    # ==========================================
    st.markdown("---")
    st.subheader("📈 3. สรุปผล Dashboard")

    if not df_filtered.empty:
        # 6.1 KPI Cards (สรุปตัวเลข)
        if num_cols:
            st.caption("สรุปยอดรวมจากข้อมูลที่เลือก")
            cols_metric = st.columns(min(len(num_cols), 4))
            for i, col_name in enumerate(num_cols[:4]):
                val = df_filtered[col_name].sum()
                cols_metric[i].metric(f"ผลรวม {col_name}", f"{val:,.0f}")
            st.markdown("---")

        # 6.2 Auto Graphs (สร้างกราฟอัตโนมัติ)
        g1, g2 = st.columns([2, 1])
        
        with g1:
            # ถ้ามีวันที่ -> กราฟเส้น
            if date_col and num_cols:
                y_axis = st.selectbox("เลือกแกน Y (แนวโน้ม):", num_cols, key="y_line")
                fig_main = px.line(df_filtered, x=date_col, y=y_axis, markers=True, title=f"แนวโน้ม {y_axis}")
            
            # ถ้าไม่มีวันที่ -> กราฟแท่ง
            elif num_cols and cat_cols:
                x_axis = st.selectbox("เลือกแกน X (เปรียบเทียบ):", cat_cols, index=0, key="x_bar")
                y_axis = st.selectbox("เลือกแกน Y:", num_cols, index=0, key="y_bar")
                fig_main = px.bar(df_filtered, x=x_axis, y=y_axis, color=x_axis, title=f"เปรียบเทียบ {y_axis} by {x_axis}")
            
            # ถ้ามีแต่ชื่อ -> กราฟนับจำนวน
            else:
                x_axis = st.selectbox("นับจำนวนตามหัวข้อ:", cat_cols, index=0) if cat_cols else None
                fig_main = px.histogram(df_filtered, x=x_axis, title=f"จำนวนรายการแยกตาม {x_axis}") if x_axis else None
            
            if fig_main: st.plotly_chart(fig_main, use_container_width=True)

        with g2:
            # กราฟวงกลม (Pie Chart)
            if cat_cols:
                pie_col = st.selectbox("แบ่งกลุ่มตาม (Pie Chart):", cat_cols, index=min(1, len(cat_cols)-1), key="pie_select")
                if num_cols:
                    fig_pie = px.pie(df_filtered, values=num_cols[0], names=pie_col, title=f"สัดส่วน {num_cols[0]}")
                else:
                    fig_pie = px.pie(df_filtered, names=pie_col, title=f"สัดส่วนจำนวน")
                st.plotly_chart(fig_pie, use_container_width=True)
else:
    st.info("👋 กรุณาเลือกวิธีนำเข้าข้อมูล (Excel หรือ Google Sheet Link) ด้านบนเพื่อเริ่มต้น")
