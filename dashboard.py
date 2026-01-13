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

# ================= SETUP TAMPILAN =================
st.set_page_config(
    page_title="Dashboard AIGIS",
    layout="wide"
)

# ================= MQTT INIT =================
if 'mqtt_client' not in st.session_state:
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)

    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            client.subscribe(MQTT_TOPIC)

    def on_message(client, userdata, msg):
        try:
            st.session_state.data = json.loads(msg.payload.decode())
            st.session_state.connected = True
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
        "jarak": 0,
        "Bahaya": 0.0,
        "Aman": 0.0,
        "status": "Menunggu...",
        "img": None
    }

# ================= HISTORY =================
if "history" not in st.session_state:
    st.session_state.history = {
        "idx": [],
        "jarak": [],
        "bahaya": [],
        "aman": []
    }

# ================= MQTT LOOP =================
st.session_state.mqtt_client.loop(timeout=0.1)

# ================= SIMPAN DATA =================
d = st.session_state.data
idx = len(st.session_state.history["idx"])

st.session_state.history["idx"].append(idx)
st.session_state.history["jarak"].append(d["jarak"])
st.session_state.history["bahaya"].append(d["Bahaya"] * 100)
st.session_state.history["aman"].append(d["Aman"] * 100)

MAX = 100
for k in st.session_state.history:
    st.session_state.history[k] = st.session_state.history[k][-MAX:]

# ================= UI =================
st.title("Dashboard Monitoring AIGIS")

col1, col2, col3 = st.columns([1, 2, 1])

# -------- STATUS --------
with col1:
    if d["status"] == "BAHAYA":
        st.error("🚨 BAHAYA")
    elif d["status"] == "WASPADA":
        st.warning("⚠️ WASPADA")
    else:
        st.success("✅ AMAN")

    st.metric("Jarak Objek", f"{d['jarak']} cm")

# -------- KAMERA --------
with col2:
    if d["img"]:
        img = Image.open(io.BytesIO(base64.b64decode(d["img"])))
        st.image(img, use_container_width=True)
    else:
        st.info("Menunggu kamera...")

# -------- AKURASI --------
with col3:
    st.write(f"🔴 Bahaya: {d['Bahaya']*100:.2f}%")
    st.progress(d["Bahaya"])
    st.write(f"🟢 Aman: {d['Aman']*100:.2f}%")
    st.progress(d["Aman"])

# ================= GRAFIK =================
st.divider()
st.subheader("📊 Grafik Real-Time")

df = pd.DataFrame({
    "Index": st.session_state.history["idx"],
    "Jarak (cm)": st.session_state.history["jarak"],
    "Bahaya (%)": st.session_state.history["bahaya"],
    "Aman (%)": st.session_state.history["aman"]
})

# ===== STYLE CHART BERSIH (NO GRID) =====
base_chart = alt.Chart(df).encode(
    x=alt.X("Index", axis=alt.Axis(grid=False, title=None))
).properties(height=280)

# ===== GRAFIK JARAK =====
chart_jarak = base_chart.mark_line(
    color="#2563eb",
    strokeWidth=3
).encode(
    y=alt.Y(
        "Jarak (cm)",
        axis=alt.Axis(grid=False, title="Jarak (cm)")
    )
)

# ===== GRAFIK AI =====
df_ai = df.melt(
    id_vars="Index",
    value_vars=["Bahaya (%)", "Aman (%)"],
    var_name="Kondisi",
    value_name="Nilai"
)

chart_ai = alt.Chart(df_ai).mark_line(strokeWidth=3).encode(
    x=alt.X("Index", axis=alt.Axis(grid=False, title=None)),
    y=alt.Y(
        "Nilai",
        scale=alt.Scale(domain=[0, 100]),
        axis=alt.Axis(grid=False, title="Persentase (%)")
    ),
    color=alt.Color(
        "Kondisi",
        scale=alt.Scale(
            domain=["Bahaya (%)", "Aman (%)"],
            range=["red", "green"]
        ),
        legend=alt.Legend(orient="top")
    )
).properties(height=280)

g1, g2 = st.columns(2)
with g1:
    st.altair_chart(chart_jarak, use_container_width=True)

with g2:
    st.altair_chart(chart_ai, use_container_width=True)

# ================= STATUS MQTT =================
if st.session_state.connected:
    st.success("🟢 MQTT Connected")
else:
    st.warning("🟡 Waiting MQTT...")

# ================= REAL-TIME LOOP =================
time.sleep(0.1)
st.rerun()
