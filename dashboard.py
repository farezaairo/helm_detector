import streamlit as st
import json, time, base64
from io import BytesIO
from PIL import Image
from paho.mqtt import client as mqtt
from streamlit_autorefresh import st_autorefresh

# --- CONFIG DARI SECRETS ---
try:
    MQTT_BROKER = st.secrets["mqtt"]["broker"]
    MQTT_USER   = st.secrets["mqtt"]["user"]
    MQTT_PASS   = st.secrets["mqtt"]["pass"]
    DATA_TOPIC  = st.secrets["mqtt"]["topic_data"]
    IMG_TOPIC   = st.secrets["mqtt"]["topic_image"]
except Exception as e:
    st.error("Secrets belum dikonfigurasi dengan benar!")
    st.stop()

st.set_page_config(page_title="Smart Safety Helmet", layout="wide")
st_autorefresh(interval=2000, key="auto_refresh")

# --- SESSION STATE ---
if "mqtt_connected" not in st.session_state:
    st.session_state.update({
        "helm_data": {}, "images": {},
        "mqtt_status": "🔴 TERPUTUS", "mqtt_connected": False
    })

# --- CALLBACKS (VERSI LAMA & BARU) ---
def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        st.session_state.mqtt_status = "🟢 TERHUBUNG"
        st.session_state.mqtt_connected = True
        client.subscribe([(DATA_TOPIC, 0), (IMG_TOPIC, 0)])
    else:
        st.session_state.mqtt_status = f"🔴 GAGAL ({rc})"

def on_message(client, userdata, msg):
    try:
        hid = msg.topic.split("/")[1]
        payload = json.loads(msg.payload.decode())
        if msg.topic.endswith("/data"):
            st.session_state.helm_data[hid] = payload
        elif msg.topic.endswith("/image"):
            st.session_state.images[hid] = Image.open(BytesIO(base64.b64decode(payload["image"])))
    except: pass

@st.cache_resource
def get_mqtt_client():
    # SOLUSI ATTRIBUTE ERROR: Cek ketersediaan CallbackAPIVersion
    try:
        # Untuk paho-mqtt v2.x
        c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, transport="websockets")
    except AttributeError:
        # Untuk paho-mqtt v1.x (Fallback)
        c = mqtt.Client(transport="websockets")
    
    c.tls_set()
    c.tls_insecure_set(True)
    c.username_pw_set(MQTT_USER, MQTT_PASS)
    c.on_connect = on_connect
    c.on_message = on_message
    return c

client = get_mqtt_client()

# --- SIDEBAR ---
with st.sidebar:
    st.title("🪖 Control")
    if not st.session_state.mqtt_connected:
        if st.button("🔌 HUBUNGKAN SEKARANG", use_container_width=True):
            client.loop_stop()
            client.connect_async(MQTT_BROKER, 443, 60)
            client.loop_start()
            time.sleep(1)
            st.rerun()
    else:
        if st.button("❌ PUTUS KONEKSI"):
            client.loop_stop()
            client.disconnect()
            st.session_state.mqtt_connected = False
            st.rerun()
    st.subheader(st.session_state.mqtt_status)

# --- DASHBOARD UI ---
st.title("🪖 Smart Safety Helmet Dashboard")
if not st.session_state.mqtt_connected:
    st.warning("Klik tombol di sidebar untuk memulai.")
    st.stop()

if not st.session_state.helm_data:
    st.info("Menunggu data... Pastikan ESP32 mengirim data atau gunakan HiveMQ Web Client untuk kirim pesan tes.")
    st.stop()

for hid, d in st.session_state.helm_data.items():
    st.divider()
    st.subheader(f"ID: {hid}")
    c1, c2, c3 = st.columns([1, 1, 2])
    with c1:
        st.metric("Jarak", f"{d.get('jarak')} cm")
        if d.get("status") == "BAHAYA": st.error("🚨 BAHAYA")
        else: st.success("✅ AMAN")
    with c2:
        st.metric("Akurasi", f"{d.get('akurasi',0)*100}%")
    with c3:
        if hid in st.session_state.images:
            st.image(st.session_state.images[hid], caption=f"Snapshot {hid}", width=300)