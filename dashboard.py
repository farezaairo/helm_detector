import streamlit as st
import pandas as pd
import requests # Menggunakan HTTP
import time
from streamlit_autorefresh import st_autorefresh

# --- CONFIG SHIFTR HTTP ---
# Format: https://public:public@public.cloud.shiftr.io/alpha_centauri/sensor
SHIFTR_URL = "https://public:public@public.cloud.shiftr.io/alpha_centauri/sensor"

# --- INITIALIZATION ---
if "df" not in st.session_state:
    st.session_state.df = pd.DataFrame(columns=["temperature", "distance"])

# --- UI SETUP ---
st.set_page_config(page_title="Alpha Centauri Dashboard", layout="wide")
st_autorefresh(interval=3000, key="http_refresh") # Refresh tiap 3 detik

st.title("🪐 Alpha Centauri Helm IoT Dashboard")

# --- FETCH DATA VIA HTTP GET ---
try:
    response = requests.get(SHIFTR_URL, timeout=2)
    if response.status_code == 200:
        data = response.json()
        new_row = {
            "temperature": float(data.get("temperature", 0)),
            "distance": float(data.get("distance", 0))
        }
        # Tambah ke dataframe jika data berbeda dengan yang terakhir
        if st.session_state.df.empty or new_row != st.session_state.df.iloc[-1].to_dict():
            st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_row])], ignore_index=True)
        st.sidebar.success("🟢 Connected via HTTP")
    else:
        st.sidebar.warning("🟡 Waiting for data...")
except Exception as e:
    st.sidebar.error(f"🔴 Connection Error")

# --- DISPLAY ---
if len(st.session_state.df) > 50:
    st.session_state.df = st.session_state.df.tail(50)

col1, col2 = st.columns([1, 2])
with col1:
    st.subheader("📊 Statistik")
    if not st.session_state.df.empty:
        last = st.session_state.df.iloc[-1]
        st.metric("Temperature", f"{last['temperature']} °C")
        st.metric("Distance", f"{last['distance']} cm")
    else: st.info("Menunggu data...")

with col2:
    st.subheader("📈 Real-time Chart")
    if not st.session_state.df.empty:
        st.line_chart(st.session_state.df[["temperature", "distance"]])

st.dataframe(st.session_state.df.iloc[::-1], width=1200)