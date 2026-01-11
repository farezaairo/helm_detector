# ================== dashboard.py ==================
import streamlit as st
import pandas as pd
import json
from paho.mqtt import client as mqtt
from streamlit_autorefresh import st_autorefresh
import threading

# ================== CONFIGURATION ==================
MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 8000
MQTT_TOPIC = "alpha_centauri/sensor"

# ================== INITIALIZE SESSION STATE ==================
if "df" not in st.session_state:
    st.session_state.df = pd.DataFrame(columns=["temperature", "distance"])

# ================== STREAMLIT PAGE SETUP ==================
st.set_page_config(page_title="Alpha Centauri Helm IoT Dashboard", layout="wide")
st.title("🪐 Alpha Centauri Helm IoT Dashboard")

# ================== AUTO REFRESH ==================
# Refresh interval setiap 2 detik
st_autorefresh(interval=2000, key="auto_refresh")

# ================== MQTT CALLBACK ==================
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✅ Connected to MQTT broker!")
        client.subscribe(MQTT_TOPIC)
    else:
        print(f"❌ Failed to connect, return code {rc}")

def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode())
        new_row = {
            "temperature": float(data.get("temperature", 0)),
            "distance": float(data.get("distance", 0)),
        }
        st.session_state.df = pd.concat(
            [st.session_state.df, pd.DataFrame([new_row])],
            ignore_index=True
        )
    except Exception as e:
        print("❌ Error parsing message:", e)

# ================== MQTT THREAD ==================
def mqtt_thread():
    client = mqtt.Client(transport="websockets")
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
    client.loop_forever()

thread = threading.Thread(target=mqtt_thread, daemon=True)
thread.start()

# ================== DASHBOARD ==================
st.subheader("Data Sensor Terbaru")
st.dataframe(st.session_state.df)

st.subheader("Visualisasi Sensor")
if not st.session_state.df.empty:
    chart_data = st.session_state.df[["temperature", "distance"]].astype(float)
    st.line_chart(chart_data)
else:
    st.info("Menunggu data sensor...")

st.subheader("Statistik Sensor")
if not st.session_state.df.empty:
    st.write(st.session_state.df.describe())
