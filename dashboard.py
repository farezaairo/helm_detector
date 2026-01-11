import streamlit as st
import paho.mqtt.client as mqtt
import json, time, base64
from PIL import Image
from io import BytesIO

# 1. Setup Konfigurasi (Ambil langsung dari Secrets)
BROKER = st.secrets["mqtt"]["broker"]
USER = st.secrets["mqtt"]["user"]
PASS = st.secrets["mqtt"]["pass"]

st.set_page_config(page_title="FINAL DASHBOARD", layout="wide")

# 2. Inisialisasi State agar tidak hilang saat refresh
if "status_koneksi" not in st.session_state:
    st.session_state.status_koneksi = "🔴 TERPUTUS"
    st.session_state.data_helm = {}

# 3. Fungsi Callback (Standar v1.6.1 - Anti Error)
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        st.session_state.status_koneksi = "🟢 TERHUBUNG"
        client.subscribe("helmet/+/data")
    else:
        st.session_state.status_koneksi = f"❌ GAGAL (RC {rc})"

def on_message(client, userdata, msg):
    try:
        topic_parts = msg.topic.split("/")
        id_helm = topic_parts[1]
        payload = json.loads(msg.payload.decode())
        st.session_state.data_helm[id_helm] = payload
    except:
        pass

# 4. Inisialisasi MQTT Client
@st.cache_resource
def get_client():
    # Gunakan transport="websockets" karena port 443 adalah jalur web
    c = mqtt.Client(transport="websockets")
    c.tls_set()
    c.username_pw_set(USER, PASS)
    c.on_connect = on_connect
    c.on_message = on_message
    return c

client = get_client()

# 5. Tampilan UI
st.title("🪖 Smart Safety Helmet")
st.sidebar.subheader(f"Status: {st.session_state.status_koneksi}")

if st.sidebar.button("🔌 HUBUNGKAN SEKARANG"):
    try:
        # Gunakan port 443
        client.connect_async(BROKER, 443, 60)
        client.loop_start()
        st.toast("Mencoba menghubungkan...")
        time.sleep(2)
        st.rerun()
    except Exception as e:
        st.error(f"Error: {e}")

# Tampilkan Data jika ada
if not st.session_state.data_helm:
    st.info("Belum ada data masuk. Kirim pesan tes dari HiveMQ Web Client sekarang!")
else:
    for hid, d in st.session_state.data_helm.items():
        st.metric(label=f"ID HELM: {hid}", value=f"{d.get('jarak')} cm", delta=d.get("status"))