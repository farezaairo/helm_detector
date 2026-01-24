import streamlit as st
import paho.mqtt.client as mqtt
import json
import base64
from PIL import Image
import io
import time
import pandas as pd
import altair as alt

# ================= MQTT CONFIG =================
MQTT_BROKER = "broker.emqx.io"
MQTT_PORT = 1883
MQTT_TOPIC = "helm/safety/data"

# ================= PAGE =================
st.set_page_config(
    page_title="Smart Safety Helmet",
    layout="wide",
    page_icon="🦺"
)

# ================= CSS MODERN UI =================
st.markdown("""
<style>
.metric-card {
    background: #0f172a;
    padding: 18px;
    border-radius: 12px;
    border: 1px solid #1e293b;
}
.big-font {
    font-size: 28px;
    font-weight: bold;
}
.status-safe {
    color: #22c55e;
    font-weight: bold;
    font-size: 26px;
}
.status-warning {
    color: #f59e0b;
    font-weight: bold;
    font-size: 26px;
}
.status-danger {
    color: #ef4444;
    font-weight: bold;
    font-size: 26px;
}
</style>
""", unsafe_allow_html=True)

# ================= SIDEBAR =================
st.sidebar.title("🦺 Helmet Control Panel")

mode = st.sidebar.radio(
    "Mode Tampilan",
    ["Semua Pekerja", "Pilih Helm"]
)

st.sidebar.divider()

# ================= MQTT =================
if "mqtt_client" not in st.session_state:

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)

    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            client.subscribe(MQTT_TOPIC)
            st.session_state.connected = True
        else:
            st.session_state.connected = False

    def on_message(client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())

            # VALIDASI DATA REAL
            required = ["id_helm", "jarak", "Bahaya", "Aman", "status", "ldr"]

            if all(k in payload for k in required):
                st.session_state.data = payload

        except:
            pass

    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_BROKER, MQTT_PORT, 60)

    st.session_state.mqtt_client = client
    st.session_state.connected = False
    st.session_state.data = None

# ================= HISTORY =================
if "history" not in st.session_state:
    st.session_state.history = {}

# ================= LOOP MQTT =================
st.session_state.mqtt_client.loop(timeout=0.1)

data = st.session_state.data

if data is None:
    st.warning("Menunggu data dari ESP32...")
    st.stop()

helm_id = data["id_helm"]

# ================= SIMPAN HISTORY =================
if helm_id not in st.session_state.history:
    st.session_state.history[helm_id] = {
        "idx": [],
        "jarak": [],
        "bahaya": [],
        "aman": []
    }

h = st.session_state.history[helm_id]

idx = len(h["idx"])

h["idx"].append(idx)
h["jarak"].append(data["jarak"])
h["bahaya"].append(data["Bahaya"] * 100)
h["aman"].append(data["Aman"] * 100)

MAX = 120
for k in h:
    h[k] = h[k][-MAX:]

# ================= PILIH HELM =================
helm_list = list(st.session_state.history.keys())

if mode == "Pilih Helm":
    selected_helm = st.sidebar.multiselect(
        "Pilih ID Helm",
        helm_list,
        default=helm_list[:1]
    )
else:
    selected_helm = helm_list

# ================= HEADER =================
st.title("🦺 Smart Safety Helmet Dashboard")
st.caption("Industrial IoT • Edge AI • Real-Time Monitoring")

# ================= STATUS ATAS =================
c1, c2, c3, c4 = st.columns(4)

c1.metric("Helm Aktif", len(selected_helm))
c2.metric("MQTT", "Connected" if st.session_state.connected else "Disconnected")
c3.metric("Update", time.strftime("%H:%M:%S"))
c4.metric("ID Helm", helm_id)

st.divider()

# ================= MAIN UI =================
col1, col2, col3 = st.columns([1,2,1])

# ---------- STATUS ----------
with col1:

    status = data["status"]

    if status == "BAHAYA":
        st.markdown('<p class="status-danger">BAHAYA</p>', unsafe_allow_html=True)
    elif status == "WASPADA":
        st.markdown('<p class="status-warning">WASPADA</p>', unsafe_allow_html=True)
    else:
        st.markdown('<p class="status-safe">AMAN</p>', unsafe_allow_html=True)

    st.metric("Jarak Objek", f"{data['jarak']} cm")

    # ===== LDR DIGITAL =====
    if data["ldr"] == 0:
        st.error("Gelap")
    else:
        st.success("Terang")

# ---------- CAMERA ----------
with col2:

    if "img" in data and data["img"]:

        img = Image.open(io.BytesIO(base64.b64decode(data["img"])))
        st.image(img, use_container_width=True)

    else:
        st.info("Tidak ada frame kamera")

# ---------- AI PROBABILITY ----------
with col3:

    st.subheader("AI Confidence")

    dfp = pd.DataFrame({
        "Label": ["Bahaya", "Aman"],
        "Nilai": [data["Bahaya"] * 100, data["Aman"] * 100],
        "Color": ["Bahaya", "Aman"]
    })

    base = alt.Chart(dfp).encode(
        x=alt.X("Nilai:Q", scale=alt.Scale(domain=[0,100]), axis=None),
        y="Label:N",
        color=alt.Color(
            "Color:N",
            scale=alt.Scale(
                domain=["Bahaya","Aman"],
                range=["#ef4444","#22c55e"]
            ),
            legend=None
        )
    )

    bar = base.mark_bar(height=20, cornerRadius=8)

    text = base.mark_text(
        align="left",
        dx=5,
        color="white",
        fontWeight="bold"
    ).encode(text=alt.Text("Nilai:Q", format=".1f"))

    st.altair_chart((bar + text), use_container_width=True)

# ================= DATA MULTI HELM =================
df_all = []

for hid in selected_helm:

    h = st.session_state.history[hid]

    df_temp = pd.DataFrame({
        "Index": h["idx"],
        "Jarak": h["jarak"],
        "Bahaya": h["bahaya"],
        "Aman": h["aman"],
        "Helm": hid
    })

    df_all.append(df_temp)

if not df_all:
    st.stop()

df = pd.concat(df_all)

# ================= GRAFIK =================
st.subheader("Grafik Real-Time")

g1, g2 = st.columns(2)

with g1:

    chart = alt.Chart(df).mark_line(
        strokeWidth=3,
        interpolate="monotone"
    ).encode(
        x="Index",
        y="Jarak",
        color="Helm:N"
    ).properties(height=300)

    st.altair_chart(chart, use_container_width=True)

with g2:

    df_ai = df.melt(
        id_vars=["Index","Helm"],
        value_vars=["Bahaya","Aman"],
        var_name="Kondisi",
        value_name="Nilai"
    )

    chart2 = alt.Chart(df_ai).mark_line(
        strokeWidth=3,
        interpolate="monotone"
    ).encode(
        x="Index",
        y=alt.Y("Nilai", scale=alt.Scale(domain=[0,100])),
        color="Kondisi",
        strokeDash="Helm"
    ).properties(height=300)

    st.altair_chart(chart2, use_container_width=True)

# ================= FOOTER =================
st.divider()
st.caption("Smart Helmet System • Edge AI Vision • MQTT IoT")

# ================= LOOP =================
time.sleep(0.1)
st.rerun()
