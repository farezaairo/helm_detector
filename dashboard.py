import streamlit as st
import pandas as pd
import json
from paho.mqtt import client as mqtt
import threading
import queue
from streamlit_autorefresh import st_autorefresh

# --- CONFIG ---
MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 8000
MQTT_TOPIC = "alpha_centauri/sensor"

# --- INITIALIZATION ---
if "df" not in st.session_state:
    st.session_state.df = pd.DataFrame(columns=["temperature", "distance"])
if "data_queue" not in st.session_state:
    st.session_state.data_queue = queue.Queue()
if "status_text" not in st.session_state:
    st.session_state.status_text = "🔴 Disconnected"

# --- MQTT CALLBACKS ---
def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        st.session_state.status_text = "🟢 Connected"
        client.subscribe(MQTT_TOPIC)
    else:
        st.session_state.status_text = f"🔴 Error: {rc}"

def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode())
        row = {
            "temperature": float(data.get("temperature", 0)),
            "distance": float(data.get("distance", 0))
        }
        st.session_state.data_queue.put(row)
    except:
        pass

# --- MQTT THREAD CONTROL ---
@st.cache_resource
def start_mqtt_service():
    # Menggunakan Client ID acak agar tidak bentrok
    client = mqtt.Client(transport="websockets") 
    client.on_connect = on_connect
    client.on_message = on_message
    
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
        t = threading.Thread(target=client.loop_forever, daemon=True)
        t.start()
        return client
    except:
        return None

# Jalankan Service
start_mqtt_service()

# --- PROCESSING QUEUE ---
while not st.session_state.data_queue.empty():
    try:
        new_row = st.session_state.data_queue.get_nowait()
        st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_row])], ignore_index=True)
    except:
        break

if len(st.session_state.df) > 50:
    st.session_state.df = st.session_state.df.tail(50)

# --- UI DISPLAY ---
st.set_page_config(page_title="Alpha Centauri Dashboard", layout="wide")
st_autorefresh(interval=2000, key="mqtt_ref")

# Sidebar Status
st.sidebar.subheader("Connection Status")
st.sidebar.write(st.session_state.status_text)

st.title("🪐 Alpha Centauri Helm IoT Dashboard")

col1, col2 = st.columns([1, 2])
with col1:
    st.subheader("📊 Statistik Sensor")
    if not st.session_state.df.empty:
        last = st.session_state.df.iloc[-1]
        st.metric("Temperature", f"{last['temperature']} °C")
        st.metric("Distance", f"{last['distance']} cm")
    else:
        st.info("Menunggu data dari broker...")

with col2:
    st.subheader("📈 Visualisasi Real-time")
    if not st.session_state.df.empty:
        st.line_chart(st.session_state.df[["temperature", "distance"]])
    else:
        st.warning("Grafik akan muncul saat data diterima.")

st.divider()
st.subheader("📋 Raw Data Log")
# Menggunakan width="stretch" untuk menghilangkan DeprecationWarning
st.dataframe(st.session_state.df.iloc[::-1], width=1200)