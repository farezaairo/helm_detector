import streamlit as st
import paho.mqtt.client as mqtt
import json
import base64
from PIL import Image
import io
import time
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

# ================= KONFIGURASI MQTT =================
MQTT_BROKER = "broker.emqx.io"
MQTT_PORT = 1883
MQTT_TOPIC = "helm/safety/data"

# ================= SETUP HALAMAN =================
st.set_page_config(
    page_title="Dashboard AIGIS",
    layout="wide"
)

# ================= AUTO REFRESH (ANTI KEDIP) =================
st_autorefresh(interval=500, key="mqtt_refresh")  # 0.5 detik

# ================= MQTT SETUP =================
if "mqtt_client" not in st.session_state:
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)

    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            client.subscribe(MQTT_TOPIC)

    def on_message(client, userdata, msg):
        try:
            st.session_state.data = json.loads(msg.payload.decode())
            st.session_state.connected = True
        except:
            pass

    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_BROKER, MQTT_PORT, 60)

    st.session_state.mqtt_client = client
    st.session_state.connected = False

# ================= DATA DEFAULT =================
if "data" not in st.session_state:
    st.session_state.data = {
        "jarak": 0,
        "Bahaya": 0.0,
        "Aman": 0.0,
        "status": "Menunggu...",
        "img": None
    }

# ================= HISTORY =================
if "history" not in st.session_state:
    st.session_state.history = {
        "t": [],
        "bahaya": [],
        "aman": [],
        "jarak": []
    }

# ================= MQTT LOOP =================
st.session_state.mqtt_client.loop(timeout=0.05)

# ================= SIMPAN DATA =================
d = st.session_state.data
now = time.strftime("%H:%M:%S")

st.session_state.history["t"].append(now)
st.session_state.history["bahaya"].append(d["Bahaya"] * 100)
st.session_state.history["aman"].append(d["Aman"] * 100)
st.session_state.history["jarak"].append(d["jarak"])

MAX = 60
for k in st.session_state.history:
    st.session_state.history[k] = st.session_state.history[k][-MAX:]

# ================= DASHBOARD =================
st.title("Dashboard Monitoring AIGIS")

col1, col2, col3 = st.columns([1, 2, 1])

with col1:
    st.subheader("Status")
    if d["status"] == "BAHAYA":
        st.error("🚨 BAHAYA")
    elif d["status"] == "WASPADA":
        st.warning("⚠️ WASPADA")
    else:
        st.success("✅ AMAN")

    st.metric("Jarak", f"{d['jarak']} cm")

with col2:
    st.subheader("Kamera")
    if d["img"]:
        img = Image.open(io.BytesIO(base64.b64decode(d["img"])))
        st.image(img, use_container_width=True)

with col3:
    st.subheader("Akurasi")
    st.progress(d["Bahaya"])
    st.write(f"🔴 Bahaya: {d['Bahaya']*100:.2f}%")
    st.progress(d["Aman"])
    st.write(f"🟢 Aman: {d['Aman']*100:.2f}%")

# ================= WARNA DINAMIS =================
bahaya_color = "rgba(255,0,0,0.5)" if d["status"] == "BAHAYA" else "rgba(255,80,80,0.3)"

# ================= GRAFIK AREA AI =================
st.divider()
st.subheader("📊 Grafik Area Akurasi AI")

fig_ai = go.Figure()

fig_ai.add_trace(go.Scatter(
    x=st.session_state.history["t"],
    y=st.session_state.history["bahaya"],
    fill="tozeroy",
    name="Bahaya",
    line=dict(color="red"),
    fillcolor=bahaya_color
))

fig_ai.add_trace(go.Scatter(
    x=st.session_state.history["t"],
    y=st.session_state.history["aman"],
    fill="tozeroy",
    name="Aman",
    line=dict(color="green"),
    fillcolor="rgba(0,255,0,0.3)"
))

fig_ai.update_layout(
    yaxis=dict(range=[0,100]),
    height=350,
    template="simple_white"
)

st.plotly_chart(fig_ai, use_container_width=True)

# ================= GRAFIK AREA JARAK =================
st.subheader("📏 Grafik Area Jarak")

fig_jarak = go.Figure()

fig_jarak.add_trace(go.Scatter(
    x=st.session_state.history["t"],
    y=st.session_state.history["jarak"],
    fill="tozeroy",
    name="Jarak (cm)",
    line=dict(color="blue"),
    fillcolor="rgba(0,0,255,0.3)"
))

fig_jarak.update_layout(
    height=300,
    template="simple_white"
)

st.plotly_chart(fig_jarak, use_container_width=True)

# ================= STATUS MQTT =================
if st.session_state.connected:
    st.success("🟢 MQTT Connected")
else:
    st.warning("🟡 Waiting MQTT...")
