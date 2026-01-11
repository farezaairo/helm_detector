import streamlit as st
import pandas as pd
import json
from paho.mqtt import client as mqtt
import threading
import queue
from streamlit_autorefresh import st_autorefresh

# ================== CONFIG ==================
MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 8000
MQTT_TOPIC = "alpha_centauri/sensor"

# ================== INITIALIZATION ==================
# Inisialisasi DataFrame agar tidak error "attribute df not found"
if "df" not in st.session_state:
    st.session_state.df = pd.DataFrame(columns=["temperature", "distance"])

# Queue untuk menampung data dari thread MQTT ke main thread Streamlit
if "data_queue" not in st.session_state:
    st.session_state.data_queue = queue.Queue()

# ================== MQTT LOGIC ==================
def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        client.subscribe(MQTT_TOPIC)
        print("✅ Connected and Subscribed!")
    else:
        print(f"❌ Connection failed: {rc}")

def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode())
        new_row = {
            "temperature": float(data.get("temperature", 0)),
            "distance": float(data.get("distance", 0))
        }
        # Masukkan ke queue, JANGAN langsung ke session_state dari sini
        st.session_state.data_queue.put(new_row)
    except Exception as e:
        print(f"❌ Error parsing: {e}")

# Fungsi ini hanya dijalankan SEKALI menggunakan cache_resource
@st.cache_resource
def start_mqtt_client():
    client = mqtt.Client(client_id="", protocol=mqtt.MQTTv5, transport="websockets")
    client.on_connect = on_connect
    client.on_message = on_message
    
    client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
    
    # Jalankan loop di thread terpisah agar tidak memblokir UI
    thread = threading.Thread(target=client.loop_forever, daemon=True)
    thread.start()
    return client

# Jalankan MQTT
start_mqtt_client()

# ================== DATA PROCESSING ==================
# Ambil semua data yang ada di antrian (queue) dan masukkan ke DataFrame
new_data_added = False
while not st.session_state.data_queue.empty():
    try:
        row = st.session_state.data_queue.get_nowait()
        st.session_state.df = pd.concat(
            [st.session_state.df, pd.DataFrame([row])], 
            ignore_index=True
        )
        new_data_added = True
    except queue.Empty:
        break

# Batasi jumlah baris agar dashboard tidak lambat (opsional: ambil 100 data terakhir)
if len(st.session_state.df) > 100:
    st.session_state.df = st.session_state.df.tail(100)

# ================== STREAMLIT UI ==================
st.set_page_config(page_title="Alpha Centauri Helm IoT Dashboard", layout="wide")
st.title("🪐 Alpha Centauri Helm IoT Dashboard")

# Refresh halaman setiap 2 detik untuk mengecek data baru di queue
st_autorefresh(interval=2000, key="mqtt_refresh")

col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("📊 Statistik Sensor")
    if not st.session_state.df.empty:
        last_data = st.session_state.df.iloc[-1]
        st.metric("Temperature", f"{last_data['temperature']} °C")
        st.metric("Distance", f"{last_data['distance']} cm")
        st.write(st.session_state.df.describe())
    else:
        st.info("Menunggu data...")

with col2:
    st.subheader("📈 Visualisasi Real-time")
    if not st.session_state.df.empty:
        st.line_chart(st.session_state.df[["temperature", "distance"]])
    else:
        st.info("Belum ada data untuk grafik")

st.divider()
st.subheader("📋 Raw Data (Last 100)")
st.dataframe(st.session_state.df.iloc[::-1], use_container_width=True) # Urutan terbaru di atas