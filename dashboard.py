import streamlit as st
import paho.mqtt.client as mqtt
import json, time

# Ambil data dari Secrets
BROKER = st.secrets["mqtt"]["broker"]
USER = st.secrets["mqtt"]["user"]
PASS = st.secrets["mqtt"]["pass"]

st.set_page_config(page_title="Helmet Safety", layout="wide")

# Gunakan list sederhana untuk simpan data agar cepat
if "data" not in st.session_state:
    st.session_state.data = {}
    st.session_state.status = "🔴 TERPUTUS"

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        st.session_state.status = "🟢 TERHUBUNG"
        client.subscribe("helmet/+/data")
    else:
        st.session_state.status = f"❌ GAGAL ({rc})"

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        hid = msg.topic.split("/")[1]
        st.session_state.data[hid] = payload
    except:
        pass

# Inisialisasi Client
client = mqtt.Client(transport="websockets")
client.tls_set()
client.username_pw_set(USER, PASS)
client.on_connect = on_connect
client.on_message = on_message

# TAMPILAN DASHBOARD
st.title("🪖 Smart Safety Helmet Dashboard")
st.sidebar.subheader(f"Status: {st.session_state.status}")

if st.sidebar.button("🔌 HUBUNGKAN SEKARANG"):
    client.connect_async(BROKER, 443, 60)
    client.loop_start()
    time.sleep(2) # Beri waktu jabat tangan
    st.rerun()

if not st.session_state.data:
    st.warning("Belum ada data. Silakan klik hubungkan dan kirim pesan dari HiveMQ.")
else:
    for hid, d in st.session_state.data.items():
        st.subheader(f"Helm ID: {hid}")
        c1, c2 = st.columns(2)
        c1.metric("Jarak", f"{d.get('jarak')} cm")
        c2.metric("Status", d.get("status"))