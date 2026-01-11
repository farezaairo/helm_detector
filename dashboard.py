import streamlit as st
from paho.mqtt import client as mqtt
import time, json, base64
from io import BytesIO
from PIL import Image

# Konfigurasi dari Secrets
MQTT_BROKER = st.secrets["mqtt"]["broker"]
MQTT_USER   = st.secrets["mqtt"]["user"]
MQTT_PASS   = st.secrets["mqtt"]["pass"]

st.set_page_config(page_title="Helmet Dashboard", layout="wide")

if "connected" not in st.session_state:
    st.session_state.connected = False
    st.session_state.data = {}

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        st.session_state.connected = True
        client.subscribe("helmet/+/data")
        client.subscribe("helmet/+/image")
    else:
        st.error(f"Gagal koneksi, kode: {rc}")

def on_message(client, userdata, msg):
    hid = msg.topic.split("/")[1]
    payload = json.loads(msg.payload.decode())
    st.session_state.data[hid] = payload

@st.cache_resource
def init_mqtt():
    # Menggunakan transport websockets wajib untuk port 443
    c = mqtt.Client(transport="websockets")
    c.tls_set()
    c.username_pw_set(MQTT_USER, MQTT_PASS)
    c.on_connect = on_connect
    c.on_message = on_message
    return c

client = init_mqtt()

# UI Dashboard
st.title("🪖 Smart Safety Helmet")

if not st.session_state.connected:
    if st.button("🔌 HUBUNGKAN SEKARANG"):
        client.connect(MQTT_BROKER, 443, 60)
        client.loop_start()
        time.sleep(2)
        st.rerun()
else:
    st.success("🟢 Terhubung ke Broker HiveMQ")
    if not st.session_state.data:
        st.info("Menunggu data dari perangkat...")
    else:
        for hid, d in st.session_state.data.items():
            st.write(f"ID Helm: {hid} | Jarak: {d.get('jarak')} cm | Status: {d.get('status')}")

if st.button("🗑️ Reset Koneksi"):
    client.loop_stop()
    client.disconnect()
    st.session_state.connected = False
    st.rerun()