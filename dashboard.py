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
if "mqtt_status" not in st.session_state:
    st.session_state.mqtt_status = "🔴 Disconnected"

# --- MQTT CALLBACKS ---
def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        st.session_state.mqtt_status = "🟢 Connected to HiveMQ"
        client.subscribe(MQTT_TOPIC)
    else:
        st.session_state.mqtt_status = f"🟠 Connection Failed (Code {rc})"

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

# --- SINGLETON MQTT CLIENT ---
@st.cache_resource
def start_mqtt():
    # Gunakan Callback API versi 2 (kosongkan client_id untuk otomatis)
    client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2, 
                         transport="websockets")
    client.on_connect = on_connect
    client.on_message = on_message
    
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
        thread = threading.Thread(target=client.loop_forever, daemon=True)
        thread.start()
        return client
    except:
        return None

start_mqtt()

# --- DATA PROCESSING ---
while not st.session_state.data_queue.empty():
    new_row = st.session_state.data_queue.get()
    st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_row])], ignore_index=True)

if len(st.session_state.df) > 50:
    st.session_state.df = st.session_state.df.tail(50)

# --- UI LAYOUT ---
st.set_page_config(page_title="Alpha Centauri Dashboard", layout="wide")
st_autorefresh(interval=2000, key="refresh")

st.title("🪐 Alpha Centauri Helm IoT Dashboard")
st.sidebar.markdown(f"**Status:** {st.session_state.mqtt_status}")

col1, col2 = st.columns([1, 2])
with col1:
    st.subheader("📊 Statistik Sensor")
    if not st.session_state.df.empty:
        last = st.session_state.df.iloc[-1]
        st.metric("Suhu", f"{last['temperature']} °C")
        st.metric("Jarak", f"{last['distance']} cm")
    else:
        st.info("Menunggu data...")

with col2:
    st.subheader("📈 Visualisasi Real-time")
    if not st.session_state.df.empty:
        st.line_chart(st.session_state.df[["temperature", "distance"]])

st.subheader("📋 Raw Data (Last 50)")
# Update sesuai saran log (width="stretch")
st.dataframe(st.session_state.df.iloc[::-1], width="stretch")