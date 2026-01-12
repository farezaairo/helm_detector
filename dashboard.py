import streamlit as st
import paho.mqtt.client as mqtt
import json
import base64
from PIL import Image
import io
import time  # <--- Tambahan ini agar time.sleep() jalan

# ================= KONFIGURASI MQTT =================
MQTT_BROKER = "broker.emqx.io"
MQTT_PORT = 1883
MQTT_TOPIC = "helm/safety/data"

# ================= SETUP TAMPILAN =================
st.set_page_config(
    page_title="Dashboard AIGIS",
    page_icon="",
    layout="wide"
)

# --- 1. INISIALISASI KONEKSI HANYA SEKALI ---
if 'mqtt_client' not in st.session_state:
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, "Streamlit_Dashboard_Client")
    
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            client.subscribe(MQTT_TOPIC)
            print("MQTT Terhubung")
    
    def on_message(client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            st.session_state.data = payload
            st.session_state.connected = True
        except Exception as e:
            print(f"Error: {e}")

    client.on_connect = on_connect
    client.on_message = on_message
    
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
    except Exception as e:
        st.error(f"Gagal koneksi awal: {e}")
    
    st.session_state.mqtt_client = client
    st.session_state.connected = False

# --- 2. INISIALISASI DATA JIKA BELUM ADA ---
if 'data' not in st.session_state:
    st.session_state.data = {
        "jarak": 0,
        "Bahaya": 0.0,
        "Aman": 0.0,
        "status": "Menunggu...",
        "img": None
    }

# ===== TAMBAHAN: INISIALISASI DATA GRAFIK =====
if "history" not in st.session_state:
    st.session_state.history = {
        "jarak": [],
        "bahaya": [],
        "aman": []
    }

# --- 3. PROSES MQTT (AMBIL DATA) ---
st.session_state.mqtt_client.loop(timeout=0.1)

# --- 4. TAMPILKAN DASHBOARD ---
st.title("Dashboard Monitoring")
d = st.session_state.data

# ===== TAMBAHAN: SIMPAN DATA UNTUK GRAFIK =====
st.session_state.history["jarak"].append(d.get("jarak", 0))
st.session_state.history["bahaya"].append(d.get("Bahaya", 0.0) * 100)
st.session_state.history["aman"].append(d.get("Aman", 0.0) * 100)

# Batasi agar tidak berat
MAX_POINTS = 100
for k in st.session_state.history:
    st.session_state.history[k] = st.session_state.history[k][-MAX_POINTS:]

col1, col2, col3 = st.columns([1, 2, 1])

with col1:
    st.subheader("Status Deteksi")
    status = d.get('status', 'Unknown')
    
    if status == "BAHAYA":
        st.error(f"### 🚨 {status}")
    elif status == "WASPADA":
        st.warning(f"### ⚠️ {status}")
    else:
        st.success(f"### ✅ {status}")
    
    st.metric(label="Jarak Objek", value=f"{d.get('jarak', 0)} cm")

with col2:
    st.subheader("Kamera Real-time")
    img_base64 = d.get('img')
    
    if img_base64:
        try:
            img_data = base64.b64decode(img_base64)
            img = Image.open(io.BytesIO(img_data))
            st.image(img, use_container_width=True, caption="Feed Kamera ESP32")
        except Exception:
            st.text("Memproses gambar...")
    else:
        st.info("Menunggu gambar dari kamera...")

with col3:
    st.subheader("Akurasi AI")
    score_bahaya = d.get('Bahaya', 0.0) * 100
    score_aman = d.get('Aman', 0.0) * 100
    
    st.write(f"🔴 **Bahaya**: {score_bahaya:.2f}%")
    st.progress(score_bahaya / 100)
    
    st.write(f"🟢 **Aman**: {score_aman:.2f}%")
    st.progress(score_aman / 100)

# ===== TAMBAHAN: GRAFIK REAL-TIME =====
st.divider()
st.subheader("📈 Grafik Real-Time")

grafik1, grafik2 = st.columns(2)

with grafik1:
    st.write("📏 Jarak Objek (cm)")
    st.line_chart({
        "Jarak (cm)": st.session_state.history["jarak"]
    })

with grafik2:
    st.write("🤖 Skor AI (%)")
    st.line_chart({
        "Bahaya (%)": st.session_state.history["bahaya"],
        "Aman (%)": st.session_state.history["aman"]
    })

if st.session_state.get("connected", False):
    st.success("🟢 Terhubung ke MQTT Broker")
else:
    st.warning("🟡 Menunggu Koneksi...")

# --- 5. JADWAL RERUN ---
time.sleep(0.1)
st.rerun()
