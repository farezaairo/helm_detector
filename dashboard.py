import streamlit as st
import paho.mqtt.client as mqtt
import json, time
from streamlit.runtime.scriptrunner import add_script_run_context

# Konfigurasi dari Secrets
BROKER = st.secrets["mqtt"]["broker"]
USER = st.secrets["mqtt"]["user"]
PASS = st.secrets["mqtt"]["pass"]

st.set_page_config(page_title="Helmet Dashboard 3.11", layout="wide")

# State untuk menyimpan data
if "data_helm" not in st.session_state:
    st.session_state.data_helm = {}
if "koneksi_aktif" not in st.session_state:
    st.session_state.koneksi_aktif = False

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        st.session_state.koneksi_aktif = True
        client.subscribe("helmet/+/data")

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        hid = msg.topic.split("/")[1]
        st.session_state.data_helm[hid] = payload
    except Exception:
        pass

@st.cache_resource
def start_mqtt_stable():
    c = mqtt.Client(transport="websockets")
    c.tls_set()
    c.username_pw_set(USER, PASS)
    c.on_connect = on_connect
    c.on_message = on_message
    c.connect(BROKER, 443, 60)
    
    # Jalankan loop dan DAFTARKAN context-nya
    # Inilah kunci agar tidak muncul error 'missing ScriptRunContext'
    c.loop_start()
    return c

# Inisialisasi MQTT
client = start_mqtt_stable()

# --- BAGIAN PENTING: Daftarkan thread latar belakang ---
# Ini mengambil thread yang sedang berjalan dan memberikan izin akses ke Streamlit
import threading
for thread in threading.enumerate():
    if thread.name.startswith("Thread"):
        add_script_run_context(thread)

# --- Tampilan Dashboard ---
st.title("🪖 Smart Safety Helmet Dashboard")
st.sidebar.subheader("Status: 🟢 ONLINE" if st.session_state.koneksi_aktif else "🔴 OFFLINE")

if not st.session_state.data_helm:
    st.info("Koneksi aman. Menunggu data pertama dari Shiftr.io...")
else:
    for hid, d in st.session_state.data_helm.items():
        st.divider()
        c1, c2 = st.columns(2)
        c1.metric("ID Helm", hid)
        c2.metric("Jarak Sensor", f"{d.get('jarak')} cm", d.get("status"))

# Autorefresh untuk UI
from streamlit_autorefresh import st_autorefresh
st_autorefresh(interval=2000, key="auto_refresh_ui")