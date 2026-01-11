import streamlit as st
import paho.mqtt.client as mqtt
import threading
import json
import pandas as pd
from datetime import datetime
import plotly.express as px

# =================== CONFIG ===================
BROKER = "broker.hivemq.com"  # Ganti sesuai broker ESP32
PORT = 8000                   # WebSocket port
TOPIC = "alpha_centauri/sensor"

DISTANCE_ALERT_THRESHOLD = 10
TEMPERATURE_ALERT_THRESHOLD = 32

df = pd.DataFrame(columns=["timestamp", "temperature", "distance", "alert"])

# =================== MQTT CALLBACK ===================
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✅ Connected to MQTT broker!")
        client.subscribe(TOPIC)
    else:
        print("❌ Failed to connect, return code", rc)

def on_message(client, userdata, msg):
    global df
    try:
        payload = msg.payload.decode()
        data = json.loads(payload.replace("'", '"'))
        alert = ""
        if data.get("distance") is not None and data["distance"] < DISTANCE_ALERT_THRESHOLD:
            alert += "⚠️ Jarak terlalu dekat! "
        if data.get("temperature") is not None and data["temperature"] > TEMPERATURE_ALERT_THRESHOLD:
            alert += "🔥 Temperature tinggi!"
        data_row = {
            "timestamp": datetime.now(),
            "temperature": data.get("temperature"),
            "distance": data.get("distance"),
            "alert": alert
        }
        df = pd.concat([df, pd.DataFrame([data_row])], ignore_index=True)
        if len(df) > 100:
            df = df.iloc[-100:]
    except Exception as e:
        print("❌ Error parsing message:", e)

# =================== MQTT CLIENT ===================
def mqtt_thread():
    client = mqtt.Client(transport="websockets")
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(BROKER, PORT)
    client.loop_forever()

threading.Thread(target=mqtt_thread, daemon=True).start()

# =================== STREAMLIT UI ===================
st.set_page_config(page_title="Alpha Centauri IoT Dashboard", layout="wide")
st.title("🌌 Alpha Centauri IoT Advanced Dashboard")
st.write(f"Terhubung ke broker `{BROKER}` pada topik `{TOPIC}`")

# ------------------- Tabel Data Sensor -------------------
st.subheader("📊 Data Sensor Terbaru")
if not df.empty:
    def color_alert(row):
        if row["alert"]:
            return ["background-color: #FF9999"]*len(row)
        return [""]*len(row)
    st.dataframe(df.style.apply(color_alert, axis=1))
else:
    st.info("Menunggu data sensor...")

# ------------------- Grafik -------------------
st.subheader("📈 Grafik Sensor")
if not df.empty:
    col1, col2 = st.columns(2)
    with col1:
        fig_temp = px.line(df, x="timestamp", y="temperature", title="Temperature (°C)", markers=True)
        st.plotly_chart(fig_temp, use_container_width=True)
    with col2:
        fig_dist = px.line(df, x="timestamp", y="distance", title="Distance (cm)", markers=True)
        st.plotly_chart(fig_dist, use_container_width=True)

# ------------------- Indikator Alert -------------------
st.subheader("🚨 Alerts")
alerts = df[df["alert"] != ""].copy()
if not alerts.empty:
    for idx, row in alerts.iterrows():
        st.warning(f"{row['timestamp'].strftime('%H:%M:%S')} - {row['alert']}")
else:
    st.success("Semua sensor normal ✅")

if st.button("Refresh"):
    st.experimental_rerun()
