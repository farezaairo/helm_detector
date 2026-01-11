import streamlit as st
import json, time, base64, pandas as pd
from io import BytesIO
from PIL import Image
from paho.mqtt import client as mqtt
from streamlit_autorefresh import st_autorefresh

# --- AMBIL DARI SECRETS ---
try:
    MQTT_BROKER = st.secrets["mqtt"]["broker"]
    MQTT_USER   = st.secrets["mqtt"]["user"]
    MQTT_PASS   = st.secrets["mqtt"]["pass"]
    MQTT_PORT   = 443 
    DATA_TOPIC  = st.secrets["mqtt"]["topic_data"]
    IMG_TOPIC   = st.secrets["mqtt"]["topic_image"]
    CONF_TOPIC  = st.secrets["mqtt"]["topic_config"]
except Exception as e:
    st.error(f"Kesalahan Secrets: {e}")
    st.stop()

st.set_page_config(page_title="Smart Safety Helmet", layout="wide")
st_autorefresh(interval=2000, key="auto_refresh")

# --- SESSION STATE ---
if "mqtt_connected" not in st.session_state:
    st.session_state.update({
        "helm_data": {}, "history": {}, "images": {},
        "mqtt_status": "🔴 TERPUTUS", "mqtt_connected": False,
        "last_msg": "-", "danger_count": 0, "log": "Siap..."
    })

# --- CALLBACKS ---
def on_connect(c, u, f, rc, properties=None):
    if rc == 0:
        st.session_state.mqtt_status = "🟢 TERHUBUNG"
        st.session_state.mqtt_connected = True
        st.session_state.log = "Berhasil Masuk!"
        c.subscribe([(DATA_TOPIC, 0), (IMG_TOPIC, 0)])
    else:
        st.session_state.mqtt_status = f"🔴 GAGAL ({rc})"
        st.session_state.log = f"Ditolak Broker. Cek User/Pass."

def on_message(client, userdata, msg):
    try:
        st.session_state.last_msg = time.strftime("%H:%M:%S")
        hid = msg.topic.split("/")[1]
        payload = json.loads(msg.payload.decode())
        if msg.topic.endswith("/data"):
            payload["time"] = st.session_state.last_msg
            st.session_state.helm_data[hid] = payload
            if hid not in st.session_state.history: st.session_state.history[hid] = []
            st.session_state.history[hid].append(payload)
            st.session_state.history[hid] = st.session_state.history[hid][-20:]
        elif msg.topic.endswith("/image"):
            st.session_state.images[hid] = Image.open(BytesIO(base64.b64decode(payload["image"])))
        st.session_state.danger_count = sum(1 for h in st.session_state.helm_data.values() if h.get("status")=="BAHAYA")
    except: pass

@st.cache_resource
def get_mqtt_client():
    c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, transport="websockets")
    c.tls_set()
    c.tls_insecure_set(True) # Wajib untuk HiveMQ Cloud di Streamlit
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
            st.session_state.mqtt_status = "🟡 PROSES..."
            client.loop_stop()
            client.connect_async(MQTT_BROKER, MQTT_PORT, 60)
            client.loop_start()
            time.sleep(1)
            st.rerun()
    else:
        if st.button("❌ PUTUS KONEKSI", use_container_width=True):
            client.loop_stop()
            client.disconnect()
            st.session_state.mqtt_connected = False
            st.session_state.mqtt_status = "🔴 TERPUTUS"
            st.rerun()

    st.subheader(st.session_state.mqtt_status)
    st.caption(f"Log: {st.session_state.log}")
    st.divider()
    helm_list = ["ALL"] + list(st.session_state.helm_data.keys())
    sel_helm = st.selectbox("🎯 Pilih Helm", helm_list)

# --- DASHBOARD ---
st.title("🪖 Smart Safety Helmet Dashboard")
if not st.session_state.mqtt_connected:
    st.warning("Silakan klik tombol di sidebar.")
    st.stop()

if not st.session_state.helm_data:
    st.info("Menunggu data... Pastikan ESP32 mengirim ke topic yang benar.")
    st.stop()

for hid, d in st.session_state.helm_data.items():
    if sel_helm != "ALL" and hid != sel_helm: continue
    st.divider()
    st.subheader(f"ID: {hid}")
    c1, c2, c3 = st.columns([1, 1, 2])
    with c1:
        st.metric("Jarak", f"{d.get('jarak')} cm")
        st.write("Status:", d.get("status"))
    with c2:
        st.metric("Akurasi", f"{d.get('akurasi',0)*100}%")
    with c3:
        if hid in st.session_state.images:
            st.image(st.session_state.images[hid], width=300)