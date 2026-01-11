# dashboard.py
import streamlit as st
import pandas as pd
import json
import threading
from paho.mqtt import client as mqtt
from datetime import datetime

# ================== KONFIGURASI MQTT ==================
BROKER = "broker.hivemq.com"
PORT = 8000
TOPIC = "alpha_centauri/sensor"

# ================== INISIALISASI SESSION_STATE ==================
if "df" not in st.session_state:
    st.session_state.df = pd.DataFrame(columns=["timestamp", "temperature", "distance"])

# ================== FUNGSIONALITAS MQTT ==================
def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print("✅ Connected to MQTT broker!")
        client.subscribe(TOPIC)
    else:
        print(f"❌ Failed to connect, return code {rc}")

def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode()
        data = json.loads(payload)
        new_row = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "temperature": data.get("temperature"),
            "distance": data.get("distance")
        }
        # Update session_state safely
        df = st.session_state.df
        st.session_state.df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    except Exception as e:
        print("❌ Error parsing message:", e)

def mqtt_thread():
    client = mqtt.Client(client_id="", transport="websockets", protocol=mqtt.MQTTv311)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(BROKER, PORT)
    client.loop_forever()

# Jalankan MQTT di thread terpisah
threading.Thread(target=mqtt_thread, daemon=True).start()

# ================== STREAMLIT DASHBOARD ==================
st.set_page_config(page_title="Alpha Centauri Helm IoT Dashboard", layout="wide")
st.title("🪐 Alpha Centauri Helm IoT Dashboard")

# Tampilkan tabel data
st.subheader("Data Sensor Terbaru")
st.dataframe(st.session_state.df)

# Visualisasi data
st.subheader("Visualisasi Sensor")
if not st.session_state.df.empty:
    chart_data = st.session_state.df[["temperature", "distance"]].astype(float)
    st.line_chart(chart_data)
else:
    st.info("Menunggu data sensor...")

# Auto refresh dashboard setiap 2 detik
st_autorefresh = st.experimental_rerun
