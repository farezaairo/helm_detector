import streamlit as st
import pandas as pd
from streamlit_autorefresh import st_autorefresh

SHEET_ID = "1tJPdtFcoKGAg213iNav55PySeZaPuSxhs1ReoqAGUpI"
URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Sheet1"

st.set_page_config(page_title="Safety AI Dashboard", layout="wide")
st_autorefresh(interval=5000, key="refresh")

st.title("🛡️ Smart Safety Helmet - AI Detection")

try:
    df = pd.read_csv(URL)
    df.columns = ["Jarak", "Status AI", "Akurasi", "Image URL", "Waktu"]
    
    if not df.empty:
        last = df.iloc[-1]
        
        # UI Metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Jarak Objek", f"{last['Jarak']} cm")
        with col2:
            st.metric("Status Keamanan", last['Status AI'])
        with col3:
            # Menampilkan akurasi dalam persen
            st.metric("Confidence Score", f"{last['Akurasi'] * 100:.1f}%")

        # Display Image
        st.subheader("📷 Bukti Tangkapan Layar")
        st.image(last['Image URL'], use_container_width=True)

    st.subheader("📊 Riwayat Deteksi")
    st.dataframe(df.iloc[::-1])

except Exception as e:
    st.info("Menunggu data dari perangkat...")