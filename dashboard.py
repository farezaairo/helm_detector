import streamlit as st
import pandas as pd
import json
from paho.mqtt import client as mqtt
import threading
import queue
from streamlit_autorefresh import st_autorefresh

# --- CONFIG BARU (SHIFTR.IO PUBLIC) ---
MQTT_BROKER = "public.cloud.shiftr.io"
MQTT_PORT = 1883
MQTT_TOPIC = "alpha_centauri/sensor"
MQTT_USER = "public"
MQTT_PASS = "public"

if "df" not in st.session_state:
    st.session_state.df = pd.DataFrame(columns=["temperature", "distance"])
if "data_queue" not in st.session_state:
    st.session_state.data_queue = queue.Queue()
if "status_text" not in st.session_state:
    st.session_state.status_text = "🟡 Menghubungkan ke Shiftr..."

def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        st.session_state.status_text = "🟢 Terhubung ke Shiftr"
        client.subscribe(MQTT_TOPIC)
    else:
        st.session_state.status_text = f"🔴 Gagal: {rc}"

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
    client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
    client.username_pw_set(MQTT_USER, MQTT_PASS) # Wajib untuk Shiftr
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

# --- PROCESSING ---
while not st.session_state.data_queue.empty():
    row = st.session_state.data_queue.get_nowait()
    st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([row])], ignore_index=True)

if len(st.session_state.df) > 50:
    st.session_state.df = st.session_state.df.tail(50)

# --- UI ---
st.set_page_config(page_title="Alpha Centauri Dashboard", layout="wide")
st_autorefresh(interval=2000, key="mqtt_ref")

st.sidebar.subheader("Status Koneksi")
st.sidebar.write(st.session_state.status_text)

st.title("🪐 Alpha Centauri Helm IoT Dashboard")

c1, c2 = st.columns([1, 2])
with c1:
    if not st.session_state.df.empty:
        last = st.session_state.df.iloc[-1]
        st.metric("Temperature", f"{last['temperature']} °C")
        st.metric("Distance", f"{last['distance']} cm")
    else: st.info("Menunggu data...")

with c2:
    if not st.session_state.df.empty:
        st.line_chart(st.session_state.df[["temperature", "distance"]])

st.dataframe(st.session_state.df.iloc[::-1], width=1000)