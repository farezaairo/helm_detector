import streamlit as st
import pandas as pd
import json
from paho.mqtt import client as mqtt
import threading
import queue
from streamlit_autorefresh import st_autorefresh

# --- CONFIG ---
MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
MQTT_TOPIC = "alpha_centauri/sensor"

# --- INITIALIZATION ---
if "df" not in st.session_state:
    st.session_state.df = pd.DataFrame(columns=["temperature", "distance"])
if "data_queue" not in st.session_state:
    st.session_state.data_queue = queue.Queue()
if "status_text" not in st.session_state:
    st.session_state.status_text = "🔴 Connecting..."

# --- MQTT CALLBACKS ---
def on_connect(client, userdata, flags, reason_code, properties=None):
    if reason_code == 0:
        st.session_state.status_text = "🟢 Connected"
        client.subscribe(MQTT_TOPIC)
    else:
        st.session_state.status_text = f"🔴 Failed: {reason_code}"

def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode())
        st.session_state.data_queue.put({
            "temperature": float(data.get("temperature", 0)),
            "distance": float(data.get("distance", 0))
        })
    except:
        pass

# --- MQTT THREAD SAFETY ---
@st.cache_resource
def init_mqtt_connection():
    # Menggunakan MQTTv5 & Websockets
    client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2, 
                         transport="websockets")
    client.on_connect = on_connect
    client.on_message = on_message
    
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
        # Menjalankan loop di latar belakang
        thread = threading.Thread(target=client.loop_forever, daemon=True)
        thread.start()
        return client
    except Exception as e:
        st.session_state.status_text = f"🔴 Error: {str(e)}"
        return None

# Jalankan koneksi
init_mqtt_connection()

# --- PROCESSING DATA ---
while not st.session_state.data_queue.empty():
    try:
        row = st.session_state.data_queue.get_nowait()
        st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([row])], ignore_index=True)
    except:
        break

# Batasi data terakhir agar tidak berat
if len(st.session_state.df) > 50:
    st.session_state.df = st.session_state.df.tail(50)

# --- UI LAYOUT ---
st.set_page_config(page_title="Alpha Centauri Dashboard", layout="wide")
st_autorefresh(interval=2000, key="refresh_timer")

st.sidebar.title("Connection Status")
st.sidebar.subheader(st.session_state.status_text)

st.title("🪐 Alpha Centauri Helm IoT Dashboard")

col1, col2 = st.columns([1, 2])
with col1:
    st.subheader("📊 Statistik Sensor")
    if not st.session_state.df.empty:
        last = st.session_state.df.iloc[-1]
        st.metric("Temperature", f"{last['temperature']} °C")
        st.metric("Distance", f"{last['distance']} cm")
    else:
        st.info("Menunggu data...")

with col2:
    st.subheader("📈 Visualisasi Real-time")
    if not st.session_state.df.empty:
        st.line_chart(st.session_state.df[["temperature", "distance"]])
    else:
        st.warning("Grafik akan muncul saat data diterima.")

st.divider()
st.subheader("📋 Raw Data Log")
# Menggunakan width="stretch" untuk menghilangkan peringatan log
st.dataframe(st.session_state.df.iloc[::-1], width=1200)