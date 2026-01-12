import streamlit as st
import pandas as pd
from streamlit_autorefresh import st_autorefresh

# --- KONFIGURASI DATA ---
SHEET_ID = "1tJPdtFcoKGAg213iNav55PySeZaPuSxhs1ReoqAGUpI"
SHEET_NAME = "Sheet1"
URL_CSV = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={SHEET_NAME}"

# --- SETTING PAGE ---
st.set_page_config(
    page_title="Alpha Centauri - Smart Safety Helmet",
    page_icon="🛡️",
    layout="wide"
)

# Autorefresh setiap 5 detik
st_autorefresh(interval=5000, key="datarefresh")

st.title("🪐 Alpha Centauri - AI Safety Helmet Detection")
st.markdown("---")

try:
    # Membaca data dari Google Sheets
    df = pd.read_csv(URL_CSV)
    df.columns = ["Jarak", "Status_Keamanan", "Akurasi_AI", "Image_URL", "Waktu_Kejadian"]
    
    if not df.empty:
        last_data = df.iloc[-1]
        
        # Penentuan Label Klasifikasi Bahaya
        status = str(last_data['Status_Keamanan']).upper()
        is_danger = "BAHAYA" in status or status == "0"

        # --- BAGIAN INDIKATOR UTAMA ---
        col1, col2, col3 = st.columns(3)
        
        with col1:
            jarak = pd.to_numeric(last_data['Jarak'], errors='coerce')
            st.metric(label="📏 Jarak Objek", value=f"{jarak} cm")
            
        with col2:
            if is_danger:
                st.error("🚨 KLASIFIKASI: BAHAYA")
            else:
                st.success("✅ KLASIFIKASI: AMAN")
                
        with col3:
            try:
                acc_val = float(last_data['Akurasi_AI'])
                st.metric(label="🎯 Confidence Score", value=f"{acc_val * 100:.1f}%")
            except:
                st.metric(label="🎯 Validasi AI", value=str(last_data['Akurasi_AI']))

        st.markdown("---")

        # --- BAGIAN TAMPILAN GAMBAR & LOG ---
        left_col, right_col = st.columns([1, 1])
        
        with left_col:
            st.subheader("📷 Tangkapan Layar Terakhir")
            
            # Menampilkan Label Bahaya/Aman Tepat di Atas Gambar
            if is_danger:
                st.markdown("<h3 style='color:red; text-align:center;'>⚠️ TERDETEKSI BAHAYA</h3>", unsafe_allow_html=True)
            else:
                st.markdown("<h3 style='color:green; text-align:center;'>✅ AREA AMAN</h3>", unsafe_allow_html=True)

            img_link = str(last_data['Image_URL'])
            if "http" in img_link:
                # Menampilkan Gambar Langsung
                st.image(img_link, use_container_width=True)
                st.caption(f"Waktu Deteksi: {last_data['Waktu_Kejadian']}")
            else:
                st.warning("Menunggu link gambar dari Google Drive...")

        with right_col:
            st.subheader("📋 Riwayat Deteksi Terbaru")
            st.dataframe(df.tail(10).iloc[::-1], use_container_width=True)

    else:
        st.info("Belum ada data masuk.")

except Exception as e:
    st.error(f"Error: {e}")