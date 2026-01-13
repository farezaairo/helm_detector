import streamlit as st
import paho.mqtt.client as mqtt
import json
import base64
from PIL import Image
import io
import time
import plotly.graph_objects as go

# ================= KONFIGURASI MQTT =================
MQTT_BROKER = "broker.emqx.io"
MQTT_PORT = 1883
MQTT_TOPIC = "helm/safety/data"

# ================= SETUP HALAMAN =================
st.set_page_config(
    page_title="Dashboard AIGIS",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ================= 1. INISIALISASI SEKALI SAJA (ANTI KEDIP) =================

# Setup MQTT Client
if "mqtt_client" not in st.session_state:
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)

    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            client.subscribe(MQTT_TOPIC)

    def on_message(client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            st.session_state.data = payload
            st.session_state.connected = True
        except:
            pass

    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    st.session_state.mqtt_client = client
    st.session_state.connected = False

# Data Default
if "data" not in st.session_state:
    st.session_state.data = {
        "jarak": 0,
        "Bahaya": 0.0,
        "Aman": 0.0,
        "status": "Menunggu...",
        "img": None
    }
    st.session_state.last_img_str = "" # Untuk cek perubahan gambar

# History Data
if "history" not in st.session_state:
    st.session_state.history = {
        "t": [],
        "bahaya": [],
        "aman": [],
        "jarak": []
    }

# --- OPTIMASI GRAFIK: Buat Object Sekali Saja ---
if "fig_ai" not in st.session_state:
    st.session_state.fig_ai = go.Figure()
    st.session_state.fig_ai.update_layout(
        yaxis=dict(range=[0, 100], title="Persentase (%)"),
        height=350,
        template="simple_white",
        margin=dict(l=0, r=0, t=20, b=0)
    )

if "fig_jarak" not in st.session_state:
    st.session_state.fig_jarak = go.Figure()
    st.session_state.fig_jarak.update_layout(
        yaxis=dict(title="Jarak (cm)"),
        height=300,
        template="simple_white",
        margin=dict(l=0, r=0, t=20, b=0)
    )

# ================= 2. LOGIKA UTAMA (LOOP) =================

# Jalankan loop MQTT sebentar
st.session_state.mqtt_client.loop(timeout=0.05)

# Ambil data terbaru
d = st.session_state.data
now = time.strftime("%H:%M:%S")

# Update History (Append Data)
st.session_state.history["t"].append(now)
st.session_state.history["bahaya"].append(d["Bahaya"] * 100)
st.session_state.history["aman"].append(d["Aman"] * 100)
st.session_state.history["jarak"].append(d["jarak"])

# Batasi history agar memori tidak penuh
MAX = 60
for k in st.session_state.history:
    st.session_state.history[k] = st.session_state.history[k][-MAX:]

# ================= 3. RENDER TAMPILAN =================

# Header
st.title("Dashboard Monitoring AIGIS")

col1, col2, col3 = st.columns([1, 2, 1])

# --- Kolom 1: Status & Metric ---
with col1:
    st.subheader("Status Sistem")
    if d["status"] == "BAHAYA":
        st.error("🚨 BAHAYA TERDETEKSI")
    elif d["status"] == "WASPADA":
        st.warning("⚠️ WASPADA")
    else:
        st.success("✅ KONDISI AMAN")

    st.metric("Jarak Objek", f"{d['jarak']} cm")

# --- Kolom 2: Kamera ---
with col2:
    st.subheader("Live Feed")
    # OPTIMASI: Hanya render gambar jika string base64 berubah (mengurangi kedip)
    current_img_str = d.get("img", "")
    if current_img_str and current_img_str != st.session_state.last_img_str:
        try:
            img = Image.open(io.BytesIO(base64.b64decode(current_img_str)))
            st.image(img, use_container_width=True, output="auto")
            st.session_state.last_img_str = current_img_str
        except:
            st.text("Error loading image")
    elif not current_img_str:
        st.info("Menunggu sinyal kamera...")

# --- Kolom 3: Akurasi ---
with col3:
    st.subheader("Akurasi AI")
    # Progress bar lebih ringan daripada grafik untuk update cepat
    st.progress(d["Bahaya"])
    st.caption(f"🔴 Bahaya: **{d['Bahaya']*100:.2f}%**")
    
    st.progress(d["Aman"])
    st.caption(f"🟢 Aman: **{d['Aman']*100:.2f}%**")

# --- Update Grafik AI (Teknik Update Data) ---
st.divider()
st.subheader("📊 Tren Akurasi AI")

# Tentukan warna dinamis
bahaya_color = "rgba(255,0,0,0.5)" if d["status"] == "BAHAYA" else "rgba(255,80,80,0.3)"

# Update data trace tanpa membuat Figure baru (Ini kunci kehalusan!)
# Gunakan selector untuk memastikan trace yang benar yang diupdate
st.session_state.fig_ai.update_traces(
    x=st.session_state.history["t"],
    y=st.session_state.history["bahaya"],
    selector=dict(name="Bahaya"), 
    fillcolor=bahaya_color
)

st.session_state.fig_ai.update_traces(
    x=st.session_state.history["t"],
    y=st.session_state.history["aman"],
    selector=dict(name="Aman")
)

# Render grafik
st.plotly_chart(st.session_state.fig_ai, use_container_width=True)

# --- Update Grafik Jarak ---
st.subheader("📏 Tren Jarak")

st.session_state.fig_jarak.update_traces(
    x=st.session_state.history["t"],
    y=st.session_state.history["jarak"],
    selector=dict(name="Jarak")
)

st.plotly_chart(st.session_state.fig_jarak, use_container_width=True)

# --- Status Bar ---
status_placeholder = st.empty()
if st.session_state.connected:
    status_placeholder.success("🟢 Terhubung ke MQTT Broker (Real-time)")
else:
    status_placeholder.warning("🟡 Menunggu koneksi MQTT...")

# ================= 4. SISTEM AUTO REFRESH HALUS =================
# Kita gunakan sleep loop pendek agar UI tidak 'beku'
# st.rerun akan menjalankan ulang script dari atas, tapi karena object chart
# sudah ada di session_state, perubahan jadi animasi yang mulus.
time.sleep(0.1) 
st.rerun()