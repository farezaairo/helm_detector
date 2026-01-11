import streamlit as st
import paho.mqtt.client as mqtt
import json, time

# Ambil data dari Secrets
BROKER = st.secrets["mqtt"]["broker"]
USER = st.secrets["mqtt"]["user"]
PASS = st.secrets["mqtt"]["pass"]

st.set_page_config(page_title="Helmet Safety", layout="wide")

# State untuk menyimpan data agar tidak hilang saat refresh
if "data_helm" not in st.session_state:
    st.session_state.data_helm = {}
if "koneksi_aktif" not in st.session_state:
    st.session_state.koneksi_aktif = False

# Fungsi Callback
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        st.session_state.koneksi_aktif = True
        client.subscribe("helmet/+/data")
    else:
        st.error(f"Koneksi Ditolak Broker (Kode: {rc})")

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        hid = msg.topic.split("/")[1]
        st.session_state.data_helm[hid] = payload
    except:
        pass

# Inisialisasi Client tanpa Cache
client = mqtt.Client(transport="websockets")
client.tls_set()
client.username_pw_set(USER, PASS)
client.on_connect = on_connect
client.on_message = on_message

# --- TAMPILAN DASHBOARD ---
st.title("🪖 Smart Safety Helmet Dashboard")

# Status di Sidebar
status_teks = "🟢 TERHUBUNG" if st.session_state.koneksi_aktif else "🔴 TERPUTUS"
st.sidebar.subheader(f"Status: {status_teks}")

if st.sidebar.button("🔌 HUBUNGKAN SEKARANG"):
    try:
        # Gunakan koneksi langsung (Blocking) agar Python 3.13 merespon
        client.connect(BROKER, 443, 60)
        # Menjalankan loop sebentar untuk memproses jabat tangan
        client.loop_start()
        time.sleep(3) # Memberi waktu ekstra untuk koneksi Cloud
        st.rerun()
    except Exception as e:
        st.error(f"Gagal Terhubung: {e}")

# Tampilkan Data
if not st.session_state.data_helm:
    st.warning("Belum ada data. Silakan hubungkan dan kirim pesan dari HiveMQ.")
else:
    for hid, d in st.session_state.data_helm.items():
        st.subheader(f"Helm ID: {hid}")
        c1, c2 = st.columns(2)
        c1.metric("Jarak", f"{d.get('jarak')} cm")
        c2.metric("Status", d.get("status"))