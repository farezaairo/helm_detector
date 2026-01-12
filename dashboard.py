import streamlit as st
import pandas as pd
from streamlit_autorefresh import st_autorefresh

# --- CONFIG ---
# PERBAIKAN: Hanya masukkan kodenya saja, bukan seluruh link
SHEET_ID = "1tJPdtFcoKGAg213iNav55PySeZaPuSxhs1ReoqAGUpI" 
SHEET_NAME = "Sheet1" 
# URL ini akan mengambil data dalam format CSV agar bisa dibaca Pandas
URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={SHEET_NAME}"

# --- UI SETUP ---
st.set_page_config(page_title="Alpha Centauri Dashboard", layout="wide")
st_autorefresh(interval=5000, key="datarefresh") 

st.title("🪐 Alpha Centauri Helm IoT Dashboard")

# --- FETCH DATA ---
try:
    # Membaca data langsung dari Google Sheets via CSV
    df = pd.read_csv(URL)
    
    # Memastikan kolom sesuai dengan header di Google Sheets Anda
    df = df[["temperature", "distance"]]
    
    st.sidebar.success("🟢 Connected to Sheets Database")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("📊 Statistik")
        if not df.empty:
            last = df.iloc[-1]
            st.metric("Temperature", f"{last['temperature']} °C")
            st.metric("Distance", f"{last['distance']} cm")
            st.write("Summary Statistics:")
            st.write(df.describe())
        else:
            st.info("Sheet masih kosong...")

    with col2:
        st.subheader("📈 Real-time Chart")
        if not df.empty:
            st.line_chart(df[["temperature", "distance"]])

    st.divider()
    st.subheader("📋 Raw Data Log")
    # Menampilkan data terbaru di paling atas
    st.dataframe(df.iloc[::-1], width=1200)

except Exception as e:
    st.sidebar.error("🔴 Menunggu Data / Link Salah")
    st.info("Pastikan Header di Sheet adalah 'temperature' dan 'distance' (huruf kecil semua).")
    # Menampilkan error asli untuk memudahkan debugging
    st.write(f"Debug Error: {e}")