import streamlit as st
import paho.mqtt.client as mqtt
import json, time
import threading

# Jalur impor yang aman
try:
    from streamlit.runtime.scriptrunner.script_run_context import add_script_run_context
except ImportError:
    from streamlit.runtime.scriptrunner import add_script_run_context

# Ambil kredensial Shiftr.io dari Secrets
BROKER = st.secrets["mqtt"]["broker"]
USER = st.secrets["mqtt"]["user"]
PASS = st.secrets["mqtt"]["pass"]

st.set_page_config(page_title="Helmet Dashboard Stable", layout="wide")

if "data_helm" not in st.session_state:
    st.session_state.data_helm = {}
if "status_koneksi" not in st.session_state:
    st.session_state.status_koneksi = "🔴 OFFLINE"

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        st.session_state.status_koneksi = "🟢 ONLINE"
        client.subscribe("helmet/+/data")

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        hid = msg.topic.split("/")[1]
        st.session_state.data_helm[hid] = payload
    except:
        pass

@st.cache_resource
def start_mqtt():
    c = mqtt.Client(transport="websockets")
    c.tls_set()
    c.username_pw_set(USER, PASS)
    c.on_connect = on_connect
    c.on_message = on_message
    c.connect(BROKER, 443, 60)
    c.loop_start()
    return c

# Inisialisasi MQTT
client = start_mqtt()

# PENTING: Daftarkan thread agar tidak muncul error merah di log
for thread in threading.enumerate():
    if thread.name.startswith("Thread"):
        add_script_run_context(thread)

# --- UI DASHBOARD ---
st.title("🪖 Smart Safety Helmet Dashboard")
st.sidebar.subheader(f"Status: {st.session_state.status_koneksi}")

if not st.session_state.data_helm:
    st.info("Koneksi berhasil. Silakan kirim data dari Visualizer Shiftr.io.")
else:
    for hid, d in st.session_state.data_helm.items():
        st.metric(f"ID Helm: {hid}", f"{d.get('jarak')} cm", d.get("status"))

# Autorefresh setiap 2 detik agar UI update otomatis
from streamlit_autorefresh import st_autorefresh
st_autorefresh(interval=2000, key="refresh")