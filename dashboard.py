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

# ================= SETUP HALAMAN =================
st.set_page_config(
    page_title="Dashboard AIGIS",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ================= INIT SESSION STATE (WAJIB) =================
if "last_img_str" not in st.session_state:
    st.session_state.last_img_str = ""

if "connected" not in st.session_state:
    st.session_state.connected = False

# ================= MQTT CLIENT =================
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

# ================= INIT FIGURE (SEKALI) =================
if "fig_ai" not in st.session_state:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        name="Bahaya",
        fill="tozeroy",
        line=dict(color="red"),
        fillcolor="rgba(255,0,0,0.3)"
    ))
    fig.add_trace(go.Scatter(
        name="Aman",
        fill="tozeroy",
        line=dict(color="green"),
        fillcolor="rgba(0,255,0,0.3)"
    ))
    fig.update_layout(
        yaxis=dict(range=[0, 100]),
        height=350,
        template="simple_white"
    )
    st.session_state.fig_ai = fig

if "fig_jarak" not in st.session_state:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        name="Jarak",
        fill="tozeroy",
        line=dict(color="blue"),
        fillcolor="rgba(0,0,255,0.3)"
    ))
    fig.update_layout(
        height=300,
        template="simple_white"
    )
    st.session_state.fig_jarak = fig

# ================= MQTT LOOP =================
st.session_state.mqtt_client.loop(timeout=0.05)

# ================= UPDATE DATA =================
d = st.session_state.data
now = time.strftime("%H:%M:%S")

st.session_state.history["t"].append(now)
st.session_state.history["bahaya"].append(d["Bahaya"] * 100)
st.session_state.history["aman"].append(d["Aman"] * 100)
st.session_state.history["jarak"].append(d["jarak"])

MAX = 60
for k in st.session_state.history:
    st.session_state.history[k] = st.session_state.history[k][-MAX:]

# ================= UI =================
st.title("Dashboard Monitoring AIGIS")

col1, col2, col3 = st.columns([1, 2, 1])

with col1:
    if d["status"] == "BAHAYA":
        st.error("🚨 BAHAYA")
    elif d["status"] == "WASPADA":
        st.warning("⚠️ WASPADA")
    else:
        st.success("✅ AMAN")

    st.metric("Jarak", f"{d['jarak']} cm")

with col2:
    current_img_str = d.get("img", "")
    if current_img_str and current_img_str != st.session_state.last_img_str:
        img = Image.open(io.BytesIO(base64.b64decode(current_img_str)))
        st.image(img, use_container_width=True)
        st.session_state.last_img_str = current_img_str
    elif not current_img_str:
        st.info("Menunggu kamera...")

with col3:
    st.progress(d["Bahaya"])
    st.caption(f"🔴 {d['Bahaya']*100:.2f}%")
    st.progress(d["Aman"])
    st.caption(f"🟢 {d['Aman']*100:.2f}%")

# ================= UPDATE GRAFIK =================
bahaya_color = "rgba(255,0,0,0.5)" if d["status"] == "BAHAYA" else "rgba(255,80,80,0.3)"

st.session_state.fig_ai.data[0].x = st.session_state.history["t"]
st.session_state.fig_ai.data[0].y = st.session_state.history["bahaya"]
st.session_state.fig_ai.data[0].fillcolor = bahaya_color

st.session_state.fig_ai.data[1].x = st.session_state.history["t"]
st.session_state.fig_ai.data[1].y = st.session_state.history["aman"]

st.plotly_chart(st.session_state.fig_ai, use_container_width=True)

st.session_state.fig_jarak.data[0].x = st.session_state.history["t"]
st.session_state.fig_jarak.data[0].y = st.session_state.history["jarak"]

st.plotly_chart(st.session_state.fig_jarak, use_container_width=True)

# ================= STATUS =================
if st.session_state.connected:
    st.success("🟢 MQTT Connected")
else:
    st.warning("🟡 Waiting MQTT...")

# ================= REFRESH HALUS =================
time.sleep(0.1)
st.rerun()
