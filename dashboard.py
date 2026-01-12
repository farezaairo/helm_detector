import streamlit as st
import pandas as pd
from streamlit_autorefresh import st_autorefresh

# --- CONFIG ---
# Ganti dengan ID Spreadsheet Anda
SHEET_ID = "https://docs.google.com/spreadsheets/d/1tJPdtFcoKGAg213iNav55PySeZaPuSxhs1ReoqAGUpI/edit?usp=sharing"
SHEET_NAME = "Sheet1" # Nama tab di bawah
URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={SHEET_NAME}"

# --- UI SETUP ---
st.set_page_config(page_title="Alpha Centauri Dashboard", layout="wide")
st_autorefresh(interval=5000, key="datarefresh") # Refresh tiap 5 detik

st.title("🪐 Alpha Centauri Helm IoT Dashboard")

# --- FETCH DATA ---
try:
    # Membaca data langsung dari Google Sheets
    df = pd.read_csv(URL)
    
    # Bersihkan kolom jika ada kolom kosong tak bernama
    df = df[["temperature", "distance"]]
    
    st.sidebar.success("🟢 Connected to Sheets Database")
    
    # --- DISPLAY ---
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("📊 Statistik")
        if not df.empty:
            last = df.iloc[-1]
            st.metric("Temperature", f"{last['temperature']} °C")
            st.metric("Distance", f"{last['distance']} cm")
            st.write(df.describe())
        else:
            st.info("Sheet masih kosong...")

    with col2:
        st.subheader("📈 Real-time Chart")
        if not df.empty:
            st.line_chart(df[["temperature", "distance"]])

    st.divider()
    st.subheader("📋 Raw Data Log")
    st.dataframe(df.iloc[::-1], width=1200)

except Exception as e:
    st.sidebar.error("🔴 Menunggu Data di Google Sheets")
    st.info("Pastikan Google Sheets sudah terisi data dan aksesnya adalah 'Anyone with link as Editor'.")