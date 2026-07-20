import io

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Water Level Metrics", layout="centered")
st.title("Daily Water Level Metrics")

st.write(
    "Upload a CSV of sensor water level measurements to calculate daily high, "
    "low, and average water levels."
)

uploaded_file = st.file_uploader("Upload water level CSV", type="csv")


def load_readings(file) -> pd.DataFrame:
    df = pd.read_csv(file, header=None, usecols=[0, 1], names=["date", "level"])
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["level"] = pd.to_numeric(df["level"], errors="coerce")
    df = df.dropna(subset=["date", "level"])
    return df


def calculate_daily_metrics(df: pd.DataFrame) -> pd.DataFrame:
    daily = df.groupby(df["date"].dt.date)["level"]
    metrics = pd.DataFrame(
        {
            "Daily High Average": daily.max(),
            "Daily Low Average": daily.min(),
            "Daily Average": daily.mean(),
        }
    )
    metrics.index.name = "Date"
    return metrics.round(2).sort_index()


if uploaded_file is not None:
    try:
        readings = load_readings(uploaded_file)
    except Exception as exc:
        st.error(f"Could not read this file as a water level CSV: {exc}")
        st.stop()

    if readings.empty:
        st.error("No valid date/water level rows were found in this file.")
        st.stop()

    metrics = calculate_daily_metrics(readings)

    st.subheader("Daily Metrics")
    st.dataframe(metrics, use_container_width=True)

    st.caption(
        "**How these are calculated:** each row in the uploaded file is one water "
        "level reading, timestamped by day. For every day, **Daily High Average** "
        "is the maximum reading recorded that day, **Daily Low Average** is the "
        "minimum reading recorded that day, and **Daily Average** is the mean of "
        "all readings recorded that day."
    )

    csv_buffer = io.StringIO()
    metrics.to_csv(csv_buffer)
    st.download_button(
        label="Download metrics as CSV",
        data=csv_buffer.getvalue(),
        file_name="daily_water_level_metrics.csv",
        mime="text/csv",
    )
else:
    st.info("Upload a CSV file to get started.")
