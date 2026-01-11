import streamlit as st
import pandas as pd
import json
from paho.mqtt import client as mqtt
import threading
import queue
from streamlit_autorefresh import st_autorefresh

# --- CONFIG BARU (PORT 1883) ---
MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883  
MQTT_TOPIC = "alpha_centauri/sensor"

if "df" not in st.session_state:
    st.session_state.df = pd.DataFrame(columns=["temperature", "distance"])
if "data_queue" not in st.session_state:
    st.session_state.data_queue = queue.Queue()
if "status_text" not in st.session_state:
    st.session_state.status_text = "🟡 Connecting to Port 1883..."

def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        st.session_state.status_text = "🟢 Connected (Port 1883)"
        client.subscribe(MQTT_TOPIC)
    else:
        st.session_state.status_text = f"🔴 Connection Failed: {rc}"

def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode())
        st.session_state.data_queue.put({
            "temperature": float(data.get("temperature", 0)),
            "distance": float(data.get("distance", 0))
        })
    except: pass

@st.cache_resource
def start_mqtt():
    # MENGGUNAKAN PROTOKOL STANDAR (BUKAN WEBSOCKETS)
    client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message
    
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
        thread = threading.Thread(target=client.loop_forever, daemon=True)
        thread.start()
        return client
    except Exception as e:
        st.session_state.status_text = f"🔴 Error: {str(e)}"
        return None

start_mqtt()

# --- PROSES DATA & UI ---
while not st.session_state.data_queue.empty():
    row = st.session_state.data_queue.get_nowait()
    st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([row])], ignore_index=True)

st.set_page_config(page_title="Alpha Centauri Dashboard", layout="wide")
st_autorefresh(interval=2000, key="mqtt_refresh")

st.sidebar.subheader("Connection Status")
st.sidebar.write(st.session_state.status_text)

st.title("🪐 Alpha Centauri Helm IoT Dashboard")
# ... sisa kode UI (statistik & chart) tetap sama ...