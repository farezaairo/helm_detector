# dashboard_iot_streamlit_cloud.py
import streamlit as st
import pandas as pd
import json
import threading
import queue
from datetime import datetime
import plotly.express as px
import paho.mqtt.client as mqtt
from streamlit_autorefresh import st_autorefresh

# =================== CONFIG ===================
BROKER = "broker.hivemq.com"  # Ganti sesuai broker kamu
PORT = 8000                   # WebSocket port
TOPIC = "alpha_centauri/sensor"

DISTANCE_ALERT_THRESHOLD = 10
TEMPERATURE_ALERT_THRESHOLD = 32
MAX_ROWS = 100  # maksimal data terakhir

# =================== QUEUE ===================
# Queue thread-safe untuk data MQTT
data_queue = queue.Queue()

# =================== MQTT CALLBACK ===================
def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print("✅ Connected to MQTT broker!")
        client.subscribe(TOPIC)
    else:
        print("❌ Failed to connect, code:", rc)

def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode()
        data = json.loads(payload.replace("'", '"'))
        data_queue.put(data)  # simpan ke queue, jangan akses session_state langsung
    except Exception as e:
        print("❌ Error parsing message:", e)

# =================== MQTT THREAD ===================
def mqtt_thread():
    client = mqtt.Client(client_id="", transport="websockets", protocol=mqtt.MQTTv311)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(BROKER, PORT)
    client.loop_forever()

threading.Thread(target=mqtt_thread, daemon=True).start()

# =================== STREAMLIT UI ===================
st.set_page_config(page_title="Alpha Centauri IoT Dashboard", layout="wide")
st.title("🌌 Alpha Centauri IoT Dashboard")
st.write(f"Terhubung ke broker `{BROKER}` pada topik `{TOPIC}`")

# =================== AUTO REFRESH ===================
st_autorefresh(interval=2000, key="auto_refresh")  # refresh tiap 2 detik

# =================== INIT SESSION_STATE ===================
if "df" not in st.session_state:
    st.session_state.df = pd.DataFrame(columns=["timestamp","temperature","distance","alert"])

# =================== PROCESS DATA QUEUE ===================
while not data_queue.empty():
    d = data_queue.get()
    alert = ""
    if d.get("distance") is not None and d["distance"] < DISTANCE_ALERT_THRESHOLD:
        alert += "⚠️ Jarak terlalu dekat! "
    if d.get("temperature") is not None and d["temperature"] > TEMPERATURE_ALERT_THRESHOLD:
        alert += "🔥 Temperature tinggi!"
    new_row = {
        "timestamp": datetime.now(),
        "temperature": d.get("temperature"),
        "distance": d.get("distance"),
        "alert": alert
    }
    st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_row])], ignore_index=True)
    if len(st.session_state.df) > MAX_ROWS:
        st.session_state.df = st.session_state.df.iloc[-MAX_ROWS:]

# =================== DISPLAY DATA ===================
st.subheader("📊 Data Sensor Terbaru")
if not st.session_state.df.empty:
    def color_alert(row):
        if row["alert"]:
            return ["background-color: #FF9999"]*len(row)
        return [""]*len(row)
    st.dataframe(st.session_state.df.style.apply(color_alert, axis=1))
else:
    st.info("Menunggu data sensor...")

# =================== PLOT GRAFIK ===================
st.subheader("📈 Grafik Sensor")
if not st.session_state.df.empty:
    col1, col2 = st.columns(2)
    with col1:
        fig_temp = px.line(
            st.session_state.df,
            x="timestamp",
            y="temperature",
            title="Temperature (°C)",
            markers=True
        )
        st.plotly_chart(fig_temp, use_container_width=True)
    with col2:
        fig_dist = px.line(
            st.session_state.df,
            x="timestamp",
            y="distance",
            title="Distance (cm)",
            markers=True
        )
        st.plotly_chart(fig_dist, use_container_width=True)

# =================== ALERTS ===================
st.subheader("🚨 Alerts")
alerts = st.session_state.df[st.session_state.df["alert"] != ""]
if not alerts.empty:
    for idx, row in alerts.iterrows():
        st.warning(f"{row['timestamp'].strftime('%H:%M:%S')} - {row['alert']}")
else:
    st.success("Semua sensor normal ✅")
