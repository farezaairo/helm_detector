import streamlit as st
import paho.mqtt.client as mqtt
import json
import base64
from PIL import Image
import io
import time
import plotly.graph_objects as go

# ================= KONFIGURASI MQTT =================
MQTT_BROKER = "broker.emqx.io"
MQTT_PORT = 1883
MQTT_TOPIC = "helm/safety/data"

# ================= SETUP TAMPILAN =================
st.set_page_config(
    page_title="Dashboard AIGIS",
    layout="wide"
)

# --- 1. INISIALISASI KONEKSI HANYA SEKALI ---
if 'mqtt_client' not in st.session_state:
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, "Streamlit_Dashboard_Client")

    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            client.subscribe(MQTT_TOPIC)

    def on_message(client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            st.session_state.data = payload
            st.session_state.connected = True
        except:
            pass

    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_BROKER, MQTT_PORT, 60)

    st.session_state.mqtt_client = client
    st.session_state.connected = False

# --- 2. DATA DEFAULT ---
if 'data' not in st.session_state:
    st.session_state.data = {
        "jarak": 0,
        "Bahaya": 0.0,
        "Aman": 0.0,
        "status": "Menunggu...",
        "img": None
    }

# --- HISTORY GRAFIK ---
if "history" not in st.session_state:
    st.session_state.history = {
        "t": [],
        "bahaya": [],
        "aman": []
    }

# --- 3. LOOP MQTT ---
st.session_state.mqtt_client.loop(timeout=0.1)

# --- 4. DASHBOARD ---
st.title("Dashboard Monitoring AIGIS")
d = st.session_state.data

# SIMPAN DATA KE HISTORY
st.session_state.history["t"].append(len(st.session_state.history["t"]))
st.session_state.history["bahaya"].append(d.get("Bahaya", 0.0) * 100)
st.session_state.history["aman"].append(d.get("Aman", 0.0) * 100)

MAX_POINTS = 100
for k in st.session_state.history:
    st.session_state.history[k] = st.session_state.history[k][-MAX_POINTS:]

col1, col2, col3 = st.columns([1, 2, 1])

with col1:
    st.subheader("Status Deteksi")
    status = d.get("status", "Unknown")

    if status == "BAHAYA":
        st.error(f"🚨 {status}")
    elif status == "WASPADA":
        st.warning(f"⚠️ {status}")
    else:
        st.success(f"✅ {status}")

    st.metric("Jarak Objek", f"{d.get('jarak', 0)} cm")

with col2:
    st.subheader("Kamera Real-time")
    img_base64 = d.get("img")

    if img_base64:
        img = Image.open(io.BytesIO(base64.b64decode(img_base64)))
        st.image(img, use_container_width=True)

with col3:
    st.subheader("Akurasi AI")
    st.progress(d.get("Bahaya", 0.0))
    st.write(f"🔴 Bahaya: {d.get('Bahaya', 0.0)*100:.2f}%")
    st.progress(d.get("Aman", 0.0))
    st.write(f"🟢 Aman: {d.get('Aman', 0.0)*100:.2f}%")

# ================= AREA CHART =================
st.divider()
st.subheader("📊 Grafik Area Akurasi AI (Real-Time)")

fig = go.Figure()

fig.add_trace(go.Scatter(
    x=st.session_state.history["t"],
    y=st.session_state.history["bahaya"],
    fill='tozeroy',
    name='Bahaya',
    line=dict(color='red'),
    fillcolor='rgba(255,0,0,0.3)'
))

fig.add_trace(go.Scatter(
    x=st.session_state.history["t"],
    y=st.session_state.history["aman"],
    fill='tozeroy',
    name='Aman',
    line=dict(color='green'),
    fillcolor='rgba(0,255,0,0.3)'
))

fig.update_layout(
    xaxis_title="Waktu",
    yaxis_title="Persentase (%)",
    yaxis=dict(range=[0, 100]),
    height=400,
    template="simple_white",
    legend=dict(orientation="h", y=1.15)
)

st.plotly_chart(fig, use_container_width=True)

# --- STATUS MQTT ---
if st.session_state.connected:
    st.success("🟢 Terhubung ke MQTT")
else:
    st.warning("🟡 Menunggu koneksi MQTT")

# --- AUTO REFRESH ---
time.sleep(0.1)
st.rerun()
