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
st.set_page_config(page_title="Dashboard AIGIS", layout="wide")

# ================= MQTT INIT =================
if "mqtt_client" not in st.session_state:
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
st.session_state.mqtt_client.loop(timeout=0.05)

# ================= SAVE DATA =================
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

# ================= DATAFRAME =================
df = pd.DataFrame({
    "Index": st.session_state.history["idx"],
    "Jarak (cm)": st.session_state.history["jarak"],
    "Bahaya (%)": st.session_state.history["bahaya"],
    "Aman (%)": st.session_state.history["aman"]
})

# ================= SAFETY GUARD (INI KUNCI FIX) =================
if df.empty:
    st.warning("Menunggu data AI...")
    time.sleep(0.1)
    st.rerun()

# ================= GRAFIK JARAK =================
base = alt.Chart(df).encode(
    x=alt.X("Index", axis=alt.Axis(grid=True, title=None))
)

chart_jarak = (
    base.mark_area(
        color="#60a5fa",
        opacity=0.25,
        interpolate="monotone"
    ).encode(
        y=alt.Y("Jarak (cm)", axis=alt.Axis(grid=True))
    )
    +
    base.mark_line(
        color="#2563eb",
        strokeWidth=3,
        interpolate="monotone"
    ).encode(
        y="Jarak (cm)"
    )
).properties(height=260)

# ================= GRAFIK AI (BUG FIXED) =================
df_ai = df.melt(
    id_vars="Index",
    value_vars=["Bahaya (%)", "Aman (%)"],
    var_name="Kondisi",
    value_name="Nilai"
)

# >>> JIKA df_ai KOSONG, JANGAN RENDER <<<
if df_ai.empty:
    df_ai = pd.DataFrame({
        "Index": [idx],
        "Kondisi": ["Bahaya (%)", "Aman (%)"],
        "Nilai": [0, 0]
    })

area_ai = alt.Chart(df_ai).mark_area(
    opacity=0.25,
    interpolate="monotone"
).encode(
    x=alt.X("Index", axis=alt.Axis(grid=True, title=None)),
    y=alt.Y(
        "Nilai",
        scale=alt.Scale(domain=[0, 100]),
        axis=alt.Axis(grid=True)
    ),
    color=alt.Color(
        "Kondisi",
        scale=alt.Scale(
            domain=["Bahaya (%)", "Aman (%)"],
            range=["red", "green"]
        ),
        legend=alt.Legend(orient="top")
    )
)

line_ai = alt.Chart(df_ai).mark_line(
    strokeWidth=3,
    interpolate="monotone"
).encode(
    x="Index",
    y="Nilai",
    color="Kondisi"
)

chart_ai = (area_ai + line_ai).properties(height=260)

# ================= DISPLAY =================
g1, g2 = st.columns(2)
with g1:
    st.altair_chart(chart_jarak, use_container_width=True)
with g2:
    st.altair_chart(chart_ai, use_container_width=True)

# ================= STATUS =================
if st.session_state.connected:
    st.success("🟢 MQTT Connected")
else:
    st.warning("🟡 Waiting MQTT...")

# ================= REAL-TIME =================
time.sleep(0.1)
st.rerun()
