import streamlit as st
import json
import time
import pandas as pd
import base64
from io import BytesIO
from PIL import Image
from paho.mqtt import client as mqtt
from streamlit_autorefresh import st_autorefresh

# ================== KONFIGURASI ==================
MQTT_BROKER = "broker.emqx.io"
MQTT_PORT = 1883

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
st.caption("IoT + AI Safety Monitoring | ESP32-CAM | MQTT | Streamlit Cloud")

st_autorefresh(interval=REFRESH_INTERVAL_MS, key="auto_refresh")

# ================== SESSION STATE ==================
if "helm_data" not in st.session_state:
    st.session_state.helm_data = {}

if "history" not in st.session_state:
    st.session_state.history = {}

if "images" not in st.session_state:
    st.session_state.images = {}

if "mqtt_started" not in st.session_state:
    st.session_state.mqtt_started = False

if "mqtt_status" not in st.session_state:
    st.session_state.mqtt_status = "DISCONNECTED"

if "last_message_time" not in st.session_state:
    st.session_state.last_message_time = "-"

if "selected_helm" not in st.session_state:
    st.session_state.selected_helm = "ALL"

if "global_threshold" not in st.session_state:
    st.session_state.global_threshold = 0.7

if "danger_count" not in st.session_state:
    st.session_state.danger_count = 0

# ================== MQTT CALLBACK ==================
def on_message(client, userdata, msg):
    try:
        st.session_state.mqtt_status = "CONNECTED"
        st.session_state.last_message_time = time.strftime("%H:%M:%S")

        payload = json.loads(msg.payload.decode())

        # ===== DATA SENSOR =====
        if msg.topic.startswith("helm/data"):
            helm_id = payload["id"]
            payload["time"] = time.strftime("%H:%M:%S")

            st.session_state.helm_data[helm_id] = payload

            if helm_id not in st.session_state.history:
                st.session_state.history[helm_id] = []

            st.session_state.history[helm_id].append(payload)

            if len(st.session_state.history[helm_id]) > MAX_HISTORY:
                st.session_state.history[helm_id].pop(0)

        # ===== IMAGE =====
        elif msg.topic.startswith("helm/image"):
            helm_id = payload["id"]
            image_bytes = base64.b64decode(payload["image"])
            image = Image.open(BytesIO(image_bytes))
            st.session_state.images[helm_id] = image

        # ===== HITUNG HELM BAHAYA =====
        danger = 0
        for h in st.session_state.helm_data.values():
            if h.get("status") == "BAHAYA":
                danger += 1
        st.session_state.danger_count = danger

    except Exception:
        pass

# ================== MQTT START ==================
def start_mqtt():
    client = mqtt.Client(
        client_id=f"streamlit-{int(time.time())}",
        clean_session=True
    )

    client.on_message = on_message

    def on_connect(c, u, f, rc):
        c.subscribe(MQTT_DATA_TOPIC)
        c.subscribe(MQTT_IMAGE_TOPIC)

    client.on_connect = on_connect
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_start()
    return client

if not st.session_state.mqtt_started:
    st.session_state.mqtt_client = start_mqtt()
    st.session_state.mqtt_started = True

# ================== SIDEBAR ==================
with st.sidebar:
    st.title("🪖 Helmet Control Center")

    if st.session_state.mqtt_status == "CONNECTED":
        st.success("🟢 MQTT ONLINE")
    else:
        st.error("🔴 MQTT OFFLINE")

    st.caption(f"Last Msg: {st.session_state.last_message_time}")

    if st.session_state.danger_count > 0:
        st.error(f"🚨 {st.session_state.danger_count} HELM BAHAYA")
    else:
        st.success("✅ Semua Helm Aman")

    st.divider()

    helm_list = ["ALL"] + list(st.session_state.helm_data.keys())
    st.session_state.selected_helm = st.selectbox(
        "🎯 Pilih Helm",
        helm_list
    )

    st.divider()

    st.markdown("### 🧠 Global AI Threshold")
    st.session_state.global_threshold = st.slider(
        "Threshold",
        0.3, 0.95,
        st.session_state.global_threshold,
        0.05
    )

    if st.button("📤 Broadcast ke Semua Helm"):
        for hid in st.session_state.helm_data.keys():
            topic = MQTT_CONFIG_TOPIC.format(hid)
            payload = json.dumps({
                "threshold": st.session_state.global_threshold
            })
            st.session_state.mqtt_client.publish(topic, payload)

        st.success("Threshold dikirim")

    st.divider()

    if st.button("🔄 Reconnect MQTT"):
        try:
            st.session_state.mqtt_client.loop_stop()
            st.session_state.mqtt_client.disconnect()
        except:
            pass

        st.session_state.mqtt_client = start_mqtt()
        st.session_state.mqtt_status = "CONNECTED"
        st.success("MQTT Reconnected")

    st.caption("Streamlit Cloud • ESP32 • MQTT")

# ================== DASHBOARD ==================
if not st.session_state.helm_data:
    st.info("⏳ Menunggu data dari helm ESP32...")
    st.stop()

for helm_id, d in st.session_state.helm_data.items():

    if (
        st.session_state.selected_helm != "ALL"
        and helm_id != st.session_state.selected_helm
    ):
        continue

    st.divider()
    st.subheader(f"🪖 HELM ID {helm_id}")

    col1, col2, col3, col4 = st.columns([1, 1, 1.3, 2])

    with col1:
        if d["status"] == "BAHAYA":
            st.error("⚠️ BAHAYA")
        else:
            st.success("✅ AMAN")

        st.metric("📏 Jarak (cm)", d["jarak"])
        st.metric("📡 RSSI", f"{d['rssi']} dBm")

    with col2:
        st.metric("🧠 Objek AI", d["objek"])
        st.metric("🎯 Akurasi", f"{d['akurasi']*100:.1f}%")
        st.metric("🔥 Bahaya", f"{d['bahaya']*100:.1f}%")

    with col3:
        st.markdown("### 🎛️ AI Threshold")

        threshold = st.slider(
            "Ambang Bahaya",
            0.3, 0.95,
            st.session_state.global_threshold,
            0.05,
            key=f"th_{helm_id}"
        )

        if st.button("Kirim ke Helm", key=f"send_{helm_id}"):
            payload = json.dumps({"threshold": threshold})
            topic = MQTT_CONFIG_TOPIC.format(helm_id)
            st.session_state.mqtt_client.publish(topic, payload)
            st.success("Threshold dikirim")

    with col4:
        st.markdown("### 📸 Live Snapshot")
        if helm_id in st.session_state.images:
            st.image(
                st.session_state.images[helm_id],
                use_column_width=True
            )
        else:
            st.info("Belum ada snapshot")

    history = st.session_state.history.get(helm_id, [])
    if history:
        df = pd.DataFrame(history)
        df["akurasi_percent"] = df["akurasi"] * 100

        st.markdown("### 📈 Grafik Jarak")
        st.line_chart(df.set_index("time")["jarak"])

        st.markdown("### 📊 Confidence AI")
        st.bar_chart(df.set_index("time")["akurasi_percent"])

# ================== FOOTER ==================
st.divider()
st.caption(
    "Smart Safety Helmet System | ESP32-CAM + AI + MQTT + Streamlit Cloud"
)
