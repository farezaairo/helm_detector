# dashboard_iot_advanced_threadsafe.py
import streamlit as st
import paho.mqtt.client as mqtt
import threading
import json
import pandas as pd
from datetime import datetime
import plotly.express as px
from streamlit_autorefresh import st_autorefresh

# =================== CONFIG ===================
BROKER = "broker.hivemq.com"  # ganti sesuai broker ESP32
PORT = 8000                   # WebSocket port
TOPIC = "alpha_centauri/sensor"

DISTANCE_ALERT_THRESHOLD = 10
TEMPERATURE_ALERT_THRESHOLD = 32
MAX_ROWS = 100  # maksimal data terakhir yang disimpan

# =================== SESSION STATE ===================
if "df" not in st.session_state:
    st.session_state.df = pd.DataFrame(columns=["timestamp", "temperature", "distance", "alert"])

# =================== MQTT CALLBACK ===================
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✅ Connected to MQTT broker!")
        client.subscribe(TOPIC)
    else:
        print("❌ Failed to connect, return code", rc)

def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode()
        data = json.loads(payload.replace("'", '"'))  # support single quotes
        alert = ""
        if data.get("distance") is not None and data["distance"] < DISTANCE_ALERT_THRESHOLD:
            alert += "⚠️ Jarak terlalu dekat! "
        if data.get("temperature") is not None and data["temperature"] > TEMPERATURE_ALERT_THRESHOLD:
            alert += "🔥 Temperature tinggi!"
        new_row = {
            "timestamp": datetime.now(),
            "temperature": data.get("temperature"),
            "distance": data.get("distance"),
            "alert": alert
        }
        # Thread-safe update session_state
        df_new = pd.concat([st.session_state.df, pd.DataFrame([new_row])], ignore_index=True)
        if len(df_new) > MAX_ROWS:
            df_new = df_new.iloc[-MAX_ROWS:]
        st.session_state.df = df_new
    except Exception as e:
        print("❌ Error parsing message:", e)

# =================== MQTT THREAD ===================
def mqtt_thread():
    client = mqtt.Client(transport="websockets")  # wajib WebSocket untuk Streamlit Cloud
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(BROKER, PORT)
    client.loop_forever()

threading.Thread(target=mqtt_thread, daemon=True).start()

# =================== STREAMLIT UI ===================
st.set_page_config(page_title="Alpha Centauri IoT Dashboard", layout="wide")
st.title("🌌 Alpha Centauri IoT Advanced Dashboard")
st.write(f"Terhubung ke broker `{BROKER}` pada topik `{TOPIC}`")

# ------------------- AUTO REFRESH -------------------
# Refresh setiap 2 detik
st_autorefresh(interval=2000, key="auto_refresh")

# ------------------- Tabel Data Sensor -------------------
st.subheader("📊 Data Sensor Terbaru")
if not st.session_state.df.empty:
    def color_alert(row):
        if row["alert"]:
            return ["background-color: #FF9999"]*len(row)
        return [""]*len(row)
    st.dataframe(st.session_state.df.style.apply(color_alert, axis=1))
else:
    st.info("Menunggu data sensor...")

# ------------------- Grafik Sensor -------------------
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

# ------------------- Alerts -------------------
st.subheader("🚨 Alerts")
alerts = st.session_state.df[st.session_state.df["alert"] != ""].copy()
if not alerts.empty:
    for idx, row in alerts.iterrows():
        st.warning(f"{row['timestamp'].strftime('%H:%M:%S')} - {row['alert']}")
else:
    st.success("Semua sensor normal ✅")
