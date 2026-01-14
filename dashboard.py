import streamlit as st
import paho.mqtt.client as mqtt
import json
import base64
from PIL import Image
import io
import time
import pandas as pd
import altair as alt

# ================= KONFIGURASI MQTT =================
MQTT_BROKER = "broker.emqx.io"
MQTT_PORT = 1883
MQTT_TOPIC = "helm/safety/data"

# ================= PAGE CONFIG =================
st.set_page_config(
    page_title="Smart Safety Helmet Dashboard",
    page_icon="",
    layout="wide"
)

# ================= SIDEBAR =================
st.sidebar.title("🦺 Safety Helmet Control")
st.sidebar.caption("Industrial IoT & Edge AI Monitoring")

mode = st.sidebar.radio(
    "Mode Tampilan",
    ["Semua Pekerja", "Pilih Helm"]
)

st.sidebar.divider()

# ================= MQTT INIT =================
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

            # Fallback jika ID helm belum dikirim
            payload.setdefault("id_helm", "HELM-001")

            st.session_state.data = payload
        except:
            pass

    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_BROKER, MQTT_PORT, 60)

    st.session_state.mqtt_client = client
    st.session_state.connected = False

# ================= DATA DEFAULT =================
if "data" not in st.session_state:
    st.session_state.data = {
        "id_helm": "HELM-001",
        "jarak": 0,
        "Bahaya": 0.0,
        "Aman": 0.0,
        "status": "Menunggu...",
        "img": None
    }

# ================= HISTORY PER HELM =================
if "history" not in st.session_state:
    st.session_state.history = {}

# ================= MQTT LOOP =================
st.session_state.mqtt_client.loop(timeout=0.1)

# ================= SIMPAN DATA =================
d = st.session_state.data
helm_id = d.get("id_helm", "HELM-001")

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
h["jarak"].append(d["jarak"])
h["bahaya"].append(d["Bahaya"] * 100)
h["aman"].append(d["Aman"] * 100)

MAX = 100
for k in h:
    h[k] = h[k][-MAX:]

# ================= SIDEBAR PILIH HELM =================
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
st.title(" Smart Safety Helmet Monitoring Dashboard")
st.caption("Real-Time • Edge AI • Blind Spot Mitigation")

# ================= STATUS RINGKAS =================
c1, c2, c3 = st.columns(3)
c1.metric("Helm Aktif", f"{len(selected_helm)} Unit")
c2.metric("Status MQTT", "Connected" if st.session_state.connected else "Waiting")
c3.metric("Update Terakhir", time.strftime("%H:%M:%S"))

st.divider()

# ================= UI UTAMA =================
col1, col2, col3 = st.columns([1, 2, 1])

with col1:
    if d["status"] == "BAHAYA":
        st.error(" BAHAYA")
    elif d["status"] == "WASPADA":
        st.warning(" WASPADA")
    else:
        st.success(" AMAN")

    st.metric("Jarak Objek", f"{d['jarak']} cm")
    st.caption(f"Helm ID: {helm_id}")

with col2:
    if d["img"]:
        img = Image.open(io.BytesIO(base64.b64decode(d["img"])))
        st.image(img, use_container_width=True)
    else:
        st.info("Menunggu kamera ESP32-CAM...")

with col3:
    st.subheader("Akurasi AI")

    df_progress = pd.DataFrame({
        "Label": ["Bahaya", "Aman"],
        "Nilai": [d["Bahaya"] * 100, d["Aman"] * 100],
        "Warna": ["Bahaya", "Aman"]
    })

    base = alt.Chart(df_progress).encode(
        x=alt.X("Nilai:Q", scale=alt.Scale(domain=[0, 100]), axis=None),
        y=alt.Y("Label:N", axis=alt.Axis(labelFontSize=13)),
        color=alt.Color(
            "Warna:N",
            scale=alt.Scale(
                domain=["Bahaya", "Aman"],
                range=["#dc2626", "#16a34a"]
            ),
            legend=None
        )
    )

    bar = base.mark_bar(height=18, cornerRadius=6)
    text = base.mark_text(
        align="left",
        dx=5,
        dy=1,
        color="white",
        fontWeight="bold"
    ).encode(text=alt.Text("Nilai:Q", format=".1f"))

    st.altair_chart((bar + text).properties(height=100), use_container_width=True)

# ================= DATAFRAME MULTI HELM =================
df_all = []

for hid in selected_helm:
    h = st.session_state.history[hid]
    df_temp = pd.DataFrame({
        "Index": h["idx"],
        "Jarak (cm)": h["jarak"],
        "Bahaya (%)": h["bahaya"],
        "Aman (%)": h["aman"],
        "Helm": hid
    })
    df_all.append(df_temp)

if not df_all:
    st.warning("Tidak ada helm dipilih")
    st.stop()

df = pd.concat(df_all)

# ================= GRAFIK =================
st.subheader("Grafik Real-Time")

g1, g2 = st.columns(2)

with g1:
    chart_jarak = alt.Chart(df).mark_line(
        strokeWidth=3,
        interpolate="monotone"
    ).encode(
        x="Index",
        y="Jarak (cm)",
        color="Helm:N"
    ).properties(height=280)

    st.altair_chart(chart_jarak, use_container_width=True)

with g2:
    df_ai = df.melt(
        id_vars=["Index", "Helm"],
        value_vars=["Bahaya (%)", "Aman (%)"],
        var_name="Kondisi",
        value_name="Nilai"
    )

    chart_ai = alt.Chart(df_ai).mark_line(
        strokeWidth=3,
        interpolate="monotone"
    ).encode(
        x="Index",
        y=alt.Y("Nilai", scale=alt.Scale(domain=[0, 100])),
        color="Kondisi",
        strokeDash="Helm"
    ).properties(height=280)

    st.altair_chart(chart_ai, use_container_width=True)

# ================= FOOTER =================
st.divider()
st.caption("© Smart Safety Helmet | IoT • Edge AI • Industrial Safety")

# ================= REAL-TIME LOOP =================
time.sleep(0.1)
st.rerun()
