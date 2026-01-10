import streamlit as st
import json
import time
import pandas as pd
import base64
from io import BytesIO
from PIL import Image
from paho.mqtt import client as mqtt
from streamlit_autorefresh import st_autorefresh

# ================== MQTT CONFIG (HIVEMQ CLOUD - WSS) ==================
MQTT_BROKER = "a6ba19304d3b42309f1342d59d8a5254.s1.eu.hivemq.cloud"
MQTT_PORT   = 8884

MQTT_USER = "Alpha"
MQTT_PASS = "Centauri1"

MQTT_DATA_TOPIC   = "helm/data/#"
MQTT_IMAGE_TOPIC  = "helm/image/#"
MQTT_CONFIG_TOPIC = "helm/config/{}"

REFRESH_INTERVAL_MS = 2000
MAX_HISTORY = 20

# ================== STREAMLIT SETUP ==================
st.set_page_config(
    page_title="Smart Safety Helmet Dashboard",
    layout="wide"
)

st.title("🪖 Smart Safety Helmet Dashboard")
st.caption("IoT + AI Safety Monitoring | ESP32-CAM | HiveMQ Cloud")

st_autorefresh(interval=REFRESH_INTERVAL_MS, key="auto_refresh")

# ================== SESSION STATE ==================
for k, v in {
    "helm_data": {},
    "history": {},
    "images": {},
    "mqtt_status": "DISCONNECTED",
    "last_message_time": "-",
    "selected_helm": "ALL",
    "global_threshold": 0.7,
    "danger_count": 0,
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ================== MQTT CALLBACK ==================
def on_message(client, userdata, msg):
    try:
        st.session_state.mqtt_status = "CONNECTED"
        st.session_state.last_message_time = time.strftime("%H:%M:%S")

        payload = json.loads(msg.payload.decode())

        if msg.topic.startswith("helm/data"):
            hid = payload["id"]
            payload["time"] = time.strftime("%H:%M:%S")
            st.session_state.helm_data[hid] = payload
            st.session_state.history.setdefault(hid, []).append(payload)
            st.session_state.history[hid] = st.session_state.history[hid][-MAX_HISTORY:]

        elif msg.topic.startswith("helm/image"):
            hid = payload["id"]
            img = base64.b64decode(payload["image"])
            st.session_state.images[hid] = Image.open(BytesIO(img))

        st.session_state.danger_count = sum(
            1 for h in st.session_state.helm_data.values()
            if h.get("status") == "BAHAYA"
        )
    except:
        pass

# ================== MQTT RESOURCE (ANTI TIMEOUT) ==================
@st.cache_resource
def mqtt_client():
    client = mqtt.Client(
        protocol=mqtt.MQTTv311,
        transport="websockets"
    )
    client.username_pw_set(MQTT_USER, MQTT_PASS)
    client.tls_set()

    client.on_message = on_message

    def on_connect(c, u, f, rc):
        if rc == 0:
            st.session_state.mqtt_status = "CONNECTED"
            c.subscribe(MQTT_DATA_TOPIC)
            c.subscribe(MQTT_IMAGE_TOPIC)
        else:
            st.session_state.mqtt_status = "FAILED"

    client.on_connect = on_connect

    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_start()
    return client

client = mqtt_client()

# ================== SIDEBAR ==================
with st.sidebar:
    st.title("🪖 Helmet Control Center")

    st.success("🟢 MQTT ONLINE") if st.session_state.mqtt_status == "CONNECTED" else st.error("🔴 MQTT OFFLINE")
    st.caption(f"Last Msg: {st.session_state.last_message_time}")

    st.success("✅ Semua Helm Aman") if st.session_state.danger_count == 0 else st.error(f"🚨 {st.session_state.danger_count} HELM BAHAYA")

    st.divider()

    helm_list = ["ALL"] + list(st.session_state.helm_data.keys())
    st.session_state.selected_helm = st.selectbox("🎯 Pilih Helm", helm_list)

    st.divider()

    st.session_state.global_threshold = st.slider(
        "🧠 Global AI Threshold",
        0.3, 0.95,
        st.session_state.global_threshold,
        0.05
    )

    if st.button("📤 Broadcast ke Semua Helm"):
        for hid in st.session_state.helm_data:
            client.publish(
                MQTT_CONFIG_TOPIC.format(hid),
                json.dumps({"threshold": st.session_state.global_threshold})
            )
        st.success("Threshold dikirim")

# ================== DASHBOARD ==================
if not st.session_state.helm_data:
    st.info("⏳ Menunggu data dari helm ESP32...")
    st.stop()

for hid, d in st.session_state.helm_data.items():
    if st.session_state.selected_helm != "ALL" and hid != st.session_state.selected_helm:
        continue

    st.divider()
    st.subheader(f"🪖 HELM ID {hid}")

    col1, col2, col3, col4 = st.columns([1, 1, 1.3, 2])

    with col1:
        st.error("⚠️ BAHAYA") if d["status"] == "BAHAYA" else st.success("✅ AMAN")
        st.metric("📏 Jarak (cm)", d["jarak"])
        st.metric("📡 RSSI", f"{d['rssi']} dBm")

    with col2:
        st.metric("🧠 Objek AI", d["objek"])
        st.metric("🎯 Akurasi", f"{d['akurasi']*100:.1f}%")
        st.metric("🔥 Bahaya", f"{d['bahaya']*100:.1f}%")

    with col3:
        th = st.slider(
            "Ambang Bahaya",
            0.3, 0.95,
            st.session_state.global_threshold,
            0.05,
            key=f"th_{hid}"
        )
        if st.button("Kirim ke Helm", key=f"send_{hid}"):
            client.publish(
                MQTT_CONFIG_TOPIC.format(hid),
                json.dumps({"threshold": th})
            )
            st.success("Threshold dikirim")

    with col4:
        st.image(st.session_state.images[hid], use_column_width=True) if hid in st.session_state.images else st.info("Belum ada snapshot")

    df = pd.DataFrame(st.session_state.history.get(hid, []))
    if not df.empty:
        df["akurasi_percent"] = df["akurasi"] * 100
        st.line_chart(df.set_index("time")["jarak"])
        st.bar_chart(df.set_index("time")["akurasi_percent"])

st.divider()
st.caption("Smart Safety Helmet | ESP32-CAM + AI + HiveMQ Cloud + Streamlit")
