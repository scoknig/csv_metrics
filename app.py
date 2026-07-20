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

buffer_pct = st.number_input(
    "Outlier buffer (%)",
    min_value=0.0,
    max_value=49.0,
    value=0.0,
    step=1.0,
    help=(
        "Optional. Trims this percentage of the highest and lowest readings "
        "from each day before calculating metrics, to reduce the effect of "
        "storm-driven outliers. Leave at 0 to use every reading."
    ),
)
# st.caption(
#     "Optional: removes extreme readings before calculating each day's metrics, "
#     "so a storm spike doesn't skew the results. For example, entering `10` "
#     "drops the highest 10% and lowest 10% of that day's readings before the "
#     "high, low, and average are calculated. Leave at `0` to use every reading."
# )


def load_readings(file) -> pd.DataFrame:
    df = pd.read_csv(file, header=None, usecols=[0, 1], names=["date", "level"])
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["level"] = pd.to_numeric(df["level"], errors="coerce")
    df = df.dropna(subset=["date", "level"])
    return df


def _trim_outliers(values: pd.Series, buffer_pct: float) -> pd.Series:
    if buffer_pct <= 0:
        return values
    n = len(values)
    trim_count = int(n * buffer_pct / 100)
    if trim_count * 2 >= n:
        return values
    return values.sort_values().iloc[trim_count : n - trim_count]


def calculate_daily_metrics(df: pd.DataFrame, buffer_pct: float = 0.0) -> pd.DataFrame:
    daily = df.groupby(df["date"].dt.date)["level"].apply(
        lambda values: _trim_outliers(values, buffer_pct)
    )
    daily = daily.groupby(level=0)
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

    metrics = calculate_daily_metrics(readings, buffer_pct)

    st.subheader("Daily Metrics")
    st.dataframe(metrics, use_container_width=True)

    if buffer_pct > 0:
        buffer_note = (
            f" Before that, the highest and lowest {buffer_pct:g}% of readings "
            "for each day were removed as potential outliers."
        )
    else:
        buffer_note = " No outlier buffer was applied, so every reading was used."

    st.caption(
        "**How these are calculated:** each row in the uploaded file is one water "
        "level reading, timestamped by day. For every day, **Daily High Average** "
        "is the maximum reading recorded that day, **Daily Low Average** is the "
        "minimum reading recorded that day, and **Daily Average** is the mean of "
        "all readings recorded that day." + buffer_note
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
