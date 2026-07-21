import io

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Water Level Metrics", layout="centered")
st.title("Water Level Metrics")

st.write(
    "Upload a CSV of sensor water level measurements to calculate the highest "
    "and lowest observed levels, mean high/low water, mean higher-high/"
    "lower-low water, and the overall average water level."
)

uploaded_file = st.file_uploader("Upload water level CSV", type="csv")

buffer_pct = st.number_input(
    "Outlier buffer (%)",
    min_value=0.0,
    max_value=49.0,
    value=0.0,
    step=1.0,
    help=(
        "Optional. Removes this percentage of the highest and lowest readings "
        "from the entire dataset before calculating metrics, to reduce the "
        "effect of storm-driven outliers. Leave at 0 to use every reading."
    ),
)
# st.caption(
#     "Optional: removes extreme readings from the whole dataset before the "
#     "metrics are calculated, so a storm spike doesn't skew the results. For "
#     "example, entering `10` drops the highest 10% and lowest 10% of all "
#     "readings (across every day) before the high, low, and average are "
#     "calculated. Leave at `0` to use every reading."
# )


def load_readings(file) -> pd.DataFrame:
    df = pd.read_csv(file, header=None, usecols=[0, 1], names=["date", "level"])
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["level"] = pd.to_numeric(df["level"], errors="coerce")
    df = df.dropna(subset=["date", "level"])
    return df


def apply_outlier_buffer(df: pd.DataFrame, buffer_pct: float) -> pd.DataFrame:
    if buffer_pct <= 0:
        return df
    n = len(df)
    trim_count = int(n * buffer_pct / 100)
    if trim_count * 2 >= n:
        return df
    return df.sort_values("level").iloc[trim_count : n - trim_count]


def calculate_summary_metrics(df: pd.DataFrame, buffer_pct: float = 0.0) -> pd.DataFrame:
    trimmed = apply_outlier_buffer(df, buffer_pct)
    levels = trimmed["level"]
    daily = trimmed.groupby(trimmed["date"].dt.date)["level"]

    mhw = daily.max().mean()
    mlw = daily.min().mean()

    above_mhw = levels[levels > mhw]
    below_mlw = levels[levels < mlw]
    mhhw = above_mhw.mean() if not above_mhw.empty else float("nan")
    mllw = below_mlw.mean() if not below_mlw.empty else float("nan")

    summary = pd.DataFrame(
        {
            "Value": [
                round(levels.max(), 2),
                round(mhhw, 2) if pd.notna(mhhw) else None,
                round(mhw, 2),
                round(levels.mean(), 2),
                round(mlw, 2),
                round(mllw, 2) if pd.notna(mllw) else None,
                round(levels.min(), 2),
            ]
        },
        index=[
            "Highest Observed Level",
            "Mean Higher High Water (MHHW)",
            "Mean High Water (MHW)",
            "Mean Sea Level",
            "Mean Low Water (MLW)",
            "Mean Lower Low Water (MLLW)",
            "Lowest Observed Level",
        ],
    )
    summary.index.name = "Metric"
    return summary


if uploaded_file is not None:
    try:
        readings = load_readings(uploaded_file)
    except Exception as exc:
        st.error(f"Could not read this file as a water level CSV: {exc}")
        st.stop()

    if readings.empty:
        st.error("No valid date/water level rows were found in this file.")
        st.stop()

    summary = calculate_summary_metrics(readings, buffer_pct)

    st.subheader("Summary Metrics")
    st.dataframe(summary, use_container_width=True)

    if buffer_pct > 0:
        buffer_note = (
            f" Before that, the highest and lowest {buffer_pct:g}% of all "
            "readings in the dataset were removed as potential outliers."
        )
    else:
        buffer_note = " No outlier buffer was applied, so every reading was used."

    st.caption(
        "**How these are calculated:** each row in the uploaded file is one "
        "water level reading, timestamped by day. **Mean High Water (MHW)** is "
        "the mean of each day's maximum reading, and **Mean Low Water (MLW)** "
        "is the mean of each day's minimum reading. **Highest/Lowest Observed "
        "Level** are the single most extreme readings in the dataset. **Mean "
        "Higher High Water (MHHW)** is the mean of all readings above MHW, and "
        "**Mean Lower Low Water (MLLW)** is the mean of all readings below "
        "MLW. **Overall Average** is the mean of every reading." + buffer_note
    )

    csv_buffer = io.StringIO()
    summary.to_csv(csv_buffer)
    st.download_button(
        label="Download metrics as CSV",
        data=csv_buffer.getvalue(),
        file_name="water_level_metrics.csv",
        mime="text/csv",
    )
else:
    st.info("Upload a CSV file to get started.")
