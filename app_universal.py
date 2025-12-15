import ssl
ssl._create_default_https_context = ssl._create_unverified_context

import streamlit as st

import pandas as pd

import plotly.express as px

from streamlit_autorefresh import st_autorefresh



# --- 1. ตั้งค่าพื้นฐาน ---

st.set_page_config(page_title="Universal Dashboard", page_icon="🌐", layout="wide")



# ตั้งค่าให้ Refresh อัตโนมัติทุก 30 วินาที

st_autorefresh(interval=30000, key="auto_refresh")



st.title("🌐 Universal Smart Dashboard")

st.markdown("ระบบวิเคราะห์ข้อมูลอเนกประสงค์ รองรับข้อมูลทุกรูปแบบ พร้อมระบบกรองและค้นหาอัตโนมัติ")



# --- 2. เชื่อมต่อข้อมูล (Google Sheets) ---

with st.expander("🔗 ตั้งค่าแหล่งข้อมูล (Data Source)", expanded=True):

    # Link เริ่มต้น (เปลี่ยนเป็นของคุณได้เลย)

    default_url = "https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/edit?usp=sharing"

    gsheet_url = st.text_input("วางลิงก์ Google Sheet ที่นี่:", value=default_url)



@st.cache_data(ttl=0)
def load_data(url):
    # แสดง Link ที่รับเข้ามาเพื่อตรวจสอบ
    # st.write(f"DEBUG: รับลิงก์ {url}") 
    
    try:
        if "docs.google.com/spreadsheets" in url:
            # 1. แปลง Link ปกติ
            export_url = url.replace('/edit?usp=sharing', '/export?format=csv')
            export_url = export_url.replace('/edit', '/export?format=csv')
            
            # 2. จัดการเรื่อง gid (กรณีเป็น Sheet ย่อย)
            if "#gid=" in url:
                gid_part = url.split("#gid=")[1]
                export_url = f"{export_url}&gid={gid_part}"
            
            # st.write(f"DEBUG: กำลังพยายามโหลดจาก {export_url}")

            # 3. ลองโหลดข้อมูล
            df = pd.read_csv(export_url)
            return df
        else:
            return None
    except Exception as e:
        # --- จุดสำคัญ: สั่งให้มันโชว์ Error สีแดงออกมา ---
        st.error(f"❌ เกิดข้อผิดพลาดในการอ่านไฟล์: {e}")
        st.info("คำแนะนำ: ลอง copy ลิงก์ไปวางใน Browser ดูว่ามันดาวน์โหลดไฟล์ CSV ได้หรือไม่?")
        return None



df = load_data(gsheet_url)



if df is not None:

    # แยกประเภทคอลัมน์ไว้ใช้งาน

    all_cols = df.columns.tolist()

    num_cols = df.select_dtypes(include=['float64', 'int64']).columns.tolist() # คอลัมน์ตัวเลข

    cat_cols = df.select_dtypes(include=['object']).columns.tolist() # คอลัมน์ข้อความ

    

    # พยายามหาคอลัมน์ "วันที่/เวลา" อัตโนมัติ

    time_keywords = ['date', 'time', 'year', 'month', 'day', 'วัน', 'เดือน', 'ปี', 'เวลา']

    date_col = next((col for col in cat_cols if any(k in col.lower() for k in time_keywords)), None)



    # ==========================================

    # ส่วนที่ 3: ระบบกรองและค้นหา (Filter & Research)

    # ==========================================

    st.markdown("---")

    st.subheader("🔍 กรองและค้นหาข้อมูล (Research & Filter)")

    

    col_search1, col_search2, col_search3 = st.columns([1, 1, 2])

    

    with col_search1:

        # 3.1 เลือกคอลัมน์ที่จะกรอง (Dynamic Dropdown)

        filter_col = st.selectbox("1. เลือกหัวข้อที่จะกรอง:", ["(แสดงทั้งหมด)"] + cat_cols)

    

    with col_search2:

        # 3.2 เลือกค่าในคอลัมน์นั้น

        if filter_col != "(แสดงทั้งหมด)":

            unique_vals = df[filter_col].unique()

            selected_vals = st.multiselect(f"2. เลือก {filter_col}:", unique_vals, default=unique_vals)

        else:

            selected_vals = []



    with col_search3:

        # 3.3 ช่องค้นหาคำ (Text Search)

        search_query = st.text_input("3. พิมพ์คำค้นหาเพิ่มเติม (Research Keyword):", "")



    # --- Process การกรองข้อมูล ---

    df_filtered = df.copy()



    # กรองตาม Dropdown

    if filter_col != "(แสดงทั้งหมด)" and selected_vals:

        df_filtered = df_filtered[df_filtered[filter_col].isin(selected_vals)]

    

    # กรองตามคำค้นหา (Research)

    if search_query:

        mask = df_filtered.astype(str).apply(lambda x: x.str.contains(search_query, case=False, na=False)).any(axis=1)

        df_filtered = df_filtered[mask]



    # แสดงสรุปผลการค้นหา

    st.caption(f"ผลลัพธ์: พบข้อมูล {len(df_filtered)} รายการ จากทั้งหมด {len(df)} รายการ")



    # ==========================================

    # ส่วนที่ 4: การแสดงผลกราฟ (Smart Visualization)

    # ==========================================

    st.markdown("---")

    

    # ถ้าไม่มีข้อมูลหลังการกรอง ให้แจ้งเตือน

    if df_filtered.empty:

        st.warning("❌ ไม่พบข้อมูลที่ตรงกับเงื่อนไขการค้นหา")

    else:

        # 4.1 แสดง KPI Card (ผลรวมตัวเลข)

        if num_cols:

            st.subheader("📊 ผลสรุปตัวเลข (Metrics)")

            cols_metric = st.columns(min(len(num_cols), 4))

            for i, col_name in enumerate(num_cols[:4]):

                val = df_filtered[col_name].sum()

                cols_metric[i].metric(f"ผลรวม {col_name}", f"{val:,.0f}")

            st.markdown("---")



        # 4.2 สร้างกราฟอัตโนมัติ

        c1, c2 = st.columns([2, 1])

        

        # กราฟหลัก (ซ้ายมือ)

        with c1:

            # เงื่อนไข: ถ้ามีวันที่ -> กราฟเส้น (Trend)

            if date_col and num_cols:

                y_axis = st.selectbox("เลือกข้อมูลแกน Y (กราฟแนวโน้ม):", num_cols)

                fig_main = px.line(df_filtered, x=date_col, y=y_axis, markers=True, 

                                   title=f"📈 แนวโน้ม: {y_axis} ตาม {date_col}")

            

            # เงื่อนไข: ถ้าไม่มีวันที่ แต่มีตัวเลขและหมวดหมู่ -> กราฟแท่ง (Comparison)

            elif num_cols and cat_cols:

                x_axis = st.selectbox("เลือกแกน X (กราฟแท่ง):", cat_cols, index=0)

                y_axis = st.selectbox("เลือกแกน Y (ตัวเลข):", num_cols, index=0)

                fig_main = px.bar(df_filtered, x=x_axis, y=y_axis, color=x_axis, 

                                  title=f"📊 เปรียบเทียบ: {y_axis} แยกตาม {x_axis}")

            

            # เงื่อนไข: ถ้ามีแต่หมวดหมู่ ไม่มีตัวเลขเลย -> กราฟนับจำนวน (Count)

            else:

                x_axis = st.selectbox("เลือกแกน X (นับจำนวน):", cat_cols, index=0) if cat_cols else None

                if x_axis:

                    fig_main = px.histogram(df_filtered, x=x_axis, title=f"จำนวนรายการแยกตาม {x_axis}")

                else:

                    fig_main = None



            if fig_main:

                st.plotly_chart(fig_main, use_container_width=True)



        # กราฟรอง (ขวามือ) - เน้นสัดส่วน (Pie Chart)

        with c2:

            if cat_cols:

                pie_col = st.selectbox("เลือกข้อมูลสำหรับกราฟวงกลม:", cat_cols, index=min(1, len(cat_cols)-1))

                

                # ถ้ามีตัวเลข ให้รวมยอด

                if num_cols:

                    val_col = num_cols[0] # เอาตัวเลขแรกเป็น Default

                    fig_pie = px.pie(df_filtered, values=val_col, names=pie_col, title=f"🍰 สัดส่วน {val_col} ตาม {pie_col}")

                # ถ้าไม่มีตัวเลข ให้นับจำนวนแถว

                else:

                    fig_pie = px.pie(df_filtered, names=pie_col, title=f"🍰 สัดส่วนจำนวนแยกตาม {pie_col}")

                

                st.plotly_chart(fig_pie, use_container_width=True)



        # ==========================================

        # ส่วนที่ 5: ตารางข้อมูล (Data Table)

        # ==========================================

        st.markdown("---")

        st.subheader("📋 ตารางข้อมูลรายละเอียด (Data Table)")

        st.dataframe(df_filtered, use_container_width=True)

        

        # ปุ่มดาวน์โหลด

        csv = df_filtered.to_csv(index=False).encode('utf-8')

        st.download_button("⬇️ ดาวน์โหลดข้อมูลชุดนี้ (CSV)", csv, "filtered_data.csv", "text/csv")



else:

    st.info("👋 ยินดีต้อนรับ! กรุณาวางลิงก์ Google Sheet ด้านบนเพื่อเริ่มวิเคราะห์ข้อมูล")