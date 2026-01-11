import streamlit as st
import json
import time
import pandas as pd
import base64
from io import BytesIO
from PIL import Image
from paho.mqtt import client as mqtt
from streamlit_autorefresh import st_autorefresh

# ================== MQTT CONFIG (FROM SECRETS) ==================
MQTT_BROKER = st.secrets["mqtt"]["broker"]
MQTT_PORT   = 443 # Tetap gunakan 443 untuk WebSockets TLS (paling stabil di Cloud)
MQTT_USER   = st.secrets["mqtt"]["user"]
MQTT_PASS   = st.secrets["mqtt"]["pass"]

MQTT_DATA_TOPIC   = st.secrets["mqtt"]["topic_data"]    
MQTT_IMAGE_TOPIC  = st.secrets["mqtt"]["topic_image"]   
MQTT_CONFIG_TOPIC = st.secrets["mqtt"]["topic_config"]  

REFRESH_INTERVAL_MS = 2000
MAX_HISTORY = 20

st.set_page_config(
    page_title="Smart Safety Helmet Dashboard",
    layout="wide"
)

st_autorefresh(interval=REFRESH_INTERVAL_MS, key="auto_refresh")

# ================== SESSION STATE ==================
for k, v in {
    "helm_data": {},
    "history": {},
    "images": {},
    "mqtt_status": "DISCONNECTED",
    "last_message_time": "-",
    "selected_helm": "ALL",
    "global_threshold": 0.7,
    "danger_count": 0,
    "mqtt_connected": False, # Flag untuk memantau status aktif koneksi
    "mqtt_log": "Siap menghubungkan..." # Tambahan untuk memantau proses
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ================== MQTT CALLBACKS ==================
def on_message(client, userdata, msg):
    try:
        st.session_state.mqtt_status = "CONNECTED"
        st.session_state.last_message_time = time.strftime("%H:%M:%S")
        
        topic_parts = msg.topic.split("/")
        if len(topic_parts) >= 2:
            hid = topic_parts[1] 

            if msg.topic.endswith("/data"):
                payload = json.loads(msg.payload.decode())
                payload["time"] = time.strftime("%H:%M:%S")
                st.session_state.helm_data[hid] = payload
                
                if hid not in st.session_state.history:
                    st.session_state.history[hid] = []
                st.session_state.history[hid].append(payload)
                st.session_state.history[hid] = st.session_state.history[hid][-MAX_HISTORY:]

            elif msg.topic.endswith("/image"):
                payload = json.loads(msg.payload.decode())
                img_data = base64.b64decode(payload["image"])
                st.session_state.images[hid] = Image.open(BytesIO(img_data))

            st.session_state.danger_count = sum(
                1 for h in st.session_state.helm_data.values()
                if h.get("status") == "BAHAYA"
            )
    except Exception as e:
        st.session_state.mqtt_log = f"Data Error: {e}"

def on_connect(c, u, f, rc, properties=None):
    if rc == 0:
        st.session_state.mqtt_status = "CONNECTED"
        st.session_state.mqtt_connected = True
        st.session_state.mqtt_log = "🟢 Berhasil Terhubung ke HiveMQ"
        c.subscribe(MQTT_DATA_TOPIC)
        c.subscribe(MQTT_IMAGE_TOPIC)
    else:
        st.session_state.mqtt_status = f"FAILED ({rc})"
        st.session_state.mqtt_log = f"🔴 Gagal: Return Code {rc}"

# ================== MQTT RESOURCE ==================
@st.cache_resource
def get_mqtt_client():
    # WAJIB: Gunakan transport="websockets" untuk lingkungan Cloud agar port 443 tidak diblokir
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, transport="websockets")
    client.tls_set() 
    client.username_pw_set(MQTT_USER, MQTT_PASS)
    client.on_message = on_message
    client.on_connect = on_connect
    return client

client = get_mqtt_client()

# ================== SIDEBAR (DENGAN TOMBOL KONEKSI) ==================
with st.sidebar:
    st.title("🪖 Helmet Control")
    
    # Tombol Hubungkan Manual (Ide User) - Mencegah "hang" saat start
    if not st.session_state.mqtt_connected:
        if st.button("🔌 HUBUNGKAN KE BROKER", use_container_width=True):
            try:
                st.session_state.mqtt_log = "Menghubungkan via WebSockets Port 443..."
                # connect_async agar UI tetap responsif meski proses koneksi sedang berjalan
                client.connect_async(MQTT_BROKER, MQTT_PORT, keepalive=60)
                client.loop_start()
                st.session_state.mqtt_status = "CONNECTING..."
                st.rerun()
            except Exception as e:
                st.session_state.mqtt_log = f"Fatal Error: {e}"
    else:
        if st.button("❌ PUTUSKAN KONEKSI", use_container_width=True):
            client.loop_stop()
            client.disconnect()
            st.session_state.mqtt_connected = False
            st.session_state.mqtt_status = "DISCONNECTED"
            st.session_state.mqtt_log = "Koneksi diputus pengguna."
            st.rerun()

    # Status Indikator
    if st.session_state.mqtt_status == "CONNECTED":
        st.success("🟢 HiveMQ ONLINE")
    elif st.session_state.mqtt_status == "CONNECTING...":
        st.warning("🟡 MENGHUBUNGKAN...")
    else:
        st.error(f"🔴 MQTT {st.session_state.mqtt_status}")
    
    # Menampilkan Log untuk debugging langsung di UI
    st.caption(f"📜 Log: {st.session_state.mqtt_log}")
    st.caption(f"Last Msg: {st.session_state.last_message_time}")
    
    if st.session_state.danger_count == 0:
        st.success("✅ Semua Helm Aman")
    else:
        st.error(f"🚨 {st.session_state.danger_count} HELM BAHAYA")
    
    st.divider()
    helm_list = ["ALL"] + list(st.session_state.helm_data.keys())
    st.session_state.selected_helm = st.selectbox("🎯 Pilih Helm", helm_list)
    
    st.divider()
    st.session_state.global_threshold = st.slider("🧠 Global AI Threshold", 0.3, 0.95, st.session_state.global_threshold, 0.05)
    
    if st.button("📤 Broadcast ke Semua"):
        if st.session_state.mqtt_connected:
            for hid in st.session_state.helm_data:
                topic = MQTT_CONFIG_TOPIC.format(hid)
                client.publish(topic, json.dumps({"threshold": st.session_state.global_threshold}))
            st.success("Broadcast Terkirim")
        else:
            st.error("MQTT Belum Terhubung")

# ================== DASHBOARD UI ==================
st.title("🪖 Smart Safety Helmet Dashboard")
st.caption("IoT + AI Safety Monitoring | ESP32-CAM | HiveMQ Cloud MQTT")

if not st.session_state.mqtt_connected:
    st.warning("⚠️ Silakan klik tombol 'HUBUNGKAN KE BROKER' di sidebar untuk memulai monitoring.")
    st.stop()

if not st.session_state.helm_data:
    st.info("⏳ Menunggu data dari broker HiveMQ Cloud... Pastikan perangkat/dummy aktif.")
    # Menampilkan petunjuk jika koneksi sudah CONNECTED tapi data belum masuk
    st.write("Status saat ini: **Terhubung**. Jika data tidak muncul, pastikan Topic sudah sesuai.")
    st.stop()

# Loop UI tetap sama
for hid, d in st.session_state.helm_data.items():
    if st.session_state.selected_helm != "ALL" and hid != st.session_state.selected_helm:
        continue
        
    st.divider()
    st.subheader(f"🪖 HELM ID: {hid}")
    
    col1, col2, col3, col4 = st.columns([1, 1, 1.3, 2])
    
    with col1:
        if d.get("status") == "BAHAYA":
            st.error("⚠️ BAHAYA")
        else:
            st.success("✅ AMAN")
        st.metric("📏 Jarak (cm)", d.get("jarak", 0))
        st.metric("📡 RSSI", f"{d.get('rssi', 0)} dBm")
        
    with col2:
        st.metric("🧠 Objek AI", d.get("objek", "-"))
        st.metric("🎯 Akurasi", f"{d.get('akurasi', 0)*100:.1f}%")
        st.metric("🔥 Potensi", f"{d.get('bahaya', 0)*100:.1f}%")
        
    with col3:
        th = st.slider(f"Ambang {hid}", 0.3, 0.95, st.session_state.global_threshold, 0.05, key=f"th_{hid}")
        if st.button("Update Helm", key=f"send_{hid}"):
            client.publish(MQTT_CONFIG_TOPIC.format(hid), json.dumps({"threshold": th}))
            st.success(f"Sent to {hid}")
                
    with col4:
        if hid in st.session_state.images:
            st.image(st.session_state.images[hid], caption=f"Snapshot {hid}", use_container_width=True)
        else:
            st.info("Belum ada gambar")

    df = pd.DataFrame(st.session_state.history.get(hid, []))
    if not df.empty:
        df["akurasi_percent"] = df.get("akurasi", 0) * 100
        st.line_chart(df.set_index("time")["jarak"])
        st.bar_chart(df.set_index("time")["akurasi_percent"])

st.divider()
st.caption("Powered by HiveMQ Cloud & Streamlit Cloud (via WebSockets Port 443)")