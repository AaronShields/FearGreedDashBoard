# app.py — scaffold, not full app
import streamlit as st
import pandas as pd
import altair as alt
from pathlib import Path

st.set_page_config(page_title="Fear & Greed Dashboard", layout="wide")

DATA_DIR = Path("data")
FG_FILE = DATA_DIR / "fg_history.csv"
MERGED_FILE = DATA_DIR / "merged_fg_prices.csv"
ANALYSIS_DIR = DATA_DIR / "analysis"

# --------- Load data (lightweight) ----------
@st.cache_data
def load_fg():
    df = pd.read_csv(FG_FILE, parse_dates=["date"])
    # ensure expected columns: date, fg_score, fg_rating (or bucket)
    if "fg_bucket" not in df.columns:
        # derive a bucket if not present
        def bucket(s):
            if s < 25: return "extreme fear"
            if s < 45: return "fear"
            if s < 55: return "neutral"
            if s < 75: return "greed"
            return "extreme greed"
        df["fg_bucket"] = df["fg_score"].apply(bucket)
    return df

@st.cache_data
def load_merged():
    df = pd.read_csv(MERGED_FILE, parse_dates=["date"])
    # expected cols: date, ticker, close, fg_score, fg_rating/fg_bucket, ret1, fwd1, fwd5
    if "fg_bucket" not in df.columns:
        def bucket(s):
            if s < 25: return "extreme fear"
            if s < 45: return "fear"
            if s < 55: return "neutral"
            if s < 75: return "greed"
            return "extreme greed"
        df["fg_bucket"] = df["fg_score"].apply(bucket)
    return df

fg = load_fg()
merged = load_merged()

# --------- Sidebar controls ----------
st.sidebar.header("Filters")
min_d, max_d = merged["date"].min(), merged["date"].max()
date_range = st.sidebar.date_input("Date range", (min_d, max_d), min_value=min_d, max_value=max_d)

all_buckets = ["extreme fear", "fear", "neutral", "greed", "extreme greed"]
bucket = st.sidebar.selectbox("Sentiment bucket (for bounce stats)", options=["All"] + all_buckets, index=0)

tickers = sorted(merged["ticker"].unique().tolist())
sel_tickers = st.sidebar.multiselect("Indexes", options=tickers, default=tickers)

st.sidebar.markdown("---")
dl_col1, dl_col2 = st.sidebar.columns(2)
with dl_col1:
    st.download_button("FG CSV", data=fg.to_csv(index=False), file_name="fg_history.csv", mime="text/csv")
with dl_col2:
    st.download_button("Merged CSV", data=merged.to_csv(index=False), file_name="merged_fg_prices.csv", mime="text/csv")

# --------- Filtered frames ----------
mask_date = (fg["date"].between(pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])))
fg_filt = fg.loc[mask_date].copy()

m = merged.copy()
m = m[m["date"].between(pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1]))]
if sel_tickers:
    m = m[m["ticker"].isin(sel_tickers)]
if bucket != "All":
    m = m[m["fg_bucket"] == bucket]

# --------- Top row: FG score line (CNN-like) ----------
st.markdown("### Fear & Greed Index (daily)")

if fg_filt.empty:
    st.info("No data in the selected date range.")
else:
    x0 = pd.to_datetime(fg_filt["date"].min())
    x1 = pd.to_datetime(fg_filt["date"].max())
    x_domain = [x0, x1]

    band_df = pd.DataFrame({
        "bucket": ["extreme fear","fear","neutral","greed","extreme greed"],
        "y0": [0,25,45,55,75],
        "y1": [25,45,55,75,100],
        "x0": [x0]*5,
        "x1": [x1]*5,
    })

    bands = (
        alt.Chart(band_df)
          .mark_rect(opacity=0.08)
          .encode(
              x="x0:T", x2="x1:T",
              y="y0:Q", y2="y1:Q",
              color=alt.Color(
                  "bucket:N",
                  scale=alt.Scale(range=["#d73027","#fc8d59","#fee08b","#91bfdb","#4575b4"]),
                  legend=None
              ),
          )
    )

    fg_line = (
        alt.Chart(fg_filt)
          .mark_line()
          .encode(
              x=alt.X("date:T", title="Date", scale=alt.Scale(domain=x_domain)),
              y=alt.Y("fg_score:Q", title="Fear & Greed Score (0–100)"),
              tooltip=["date:T", alt.Tooltip("fg_score:Q", format=".1f"), "fg_bucket:N"]
          )
          .properties(height=260)
    )

    st.altair_chart(bands + fg_line, use_container_width=True)

# --------- Bucket averages (below the chart) ----------
st.markdown("### Average returns by Fear & Greed bucket")

# pick the frame driving stats (same filtered 'm' you built earlier)
bucket_order = ["extreme fear", "fear", "neutral", "greed", "extreme greed"]

def summarize_by_bucket(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["fg_bucket","ticker","avg_fwd1","hit_fwd1","avg_fwd5","hit_fwd5","count"])
    g = df.groupby(["fg_bucket","ticker"])
    out = (
        g.agg(
            avg_fwd1=("fwd1","mean"),
            med_fwd1=("fwd1","median"),
            hit_fwd1=("fwd1", lambda s: (s > 0).mean()),
            avg_fwd5=("fwd5","mean"),
            med_fwd5=("fwd5","median"),
            hit_fwd5=("fwd5", lambda s: (s > 0).mean()),
            count=("fwd1","count"),
        )
        .reset_index()
    )
    # order buckets nicely
    out["fg_bucket"] = pd.Categorical(out["fg_bucket"], categories=bucket_order, ordered=True)
    out = out.sort_values(["fg_bucket","ticker"]).reset_index(drop=True)
    return out

by_bucket = summarize_by_bucket(m.dropna(subset=["fwd1","fwd5"]))

# pretty table
st.dataframe(
    by_bucket[["fg_bucket","ticker","avg_fwd1","hit_fwd1","avg_fwd5","hit_fwd5","count"]]
      .rename(columns={
          "fg_bucket":"bucket",
          "avg_fwd1":"avg fwd1",
          "hit_fwd1":"hit fwd1",
          "avg_fwd5":"avg fwd5",
          "hit_fwd5":"hit fwd5"
      })
      .style.format({
          "avg fwd1":"{:.4%}",
          "hit fwd1":"{:.1%}",
          "avg fwd5":"{:.4%}",
          "hit fwd5":"{:.1%}"
      }),
    use_container_width=True
)

# optional: overall (all tickers combined) table
with st.expander("Show overall (all tickers combined)"):
    overall = (
        m.dropna(subset=["fwd1","fwd5"])
         .groupby("fg_bucket")
         .agg(
             avg_fwd1=("fwd1","mean"),
             med_fwd1=("fwd1","median"),
             hit_fwd1=("fwd1", lambda s: (s > 0).mean()),
             avg_fwd5=("fwd5","mean"),
             med_fwd5=("fwd5","median"),
             hit_fwd5=("fwd5", lambda s: (s > 0).mean()),
             count=("fwd1","count"),
         )
         .reset_index()
    )
    overall["fg_bucket"] = pd.Categorical(overall["fg_bucket"], categories=bucket_order, ordered=True)
    overall = overall.sort_values("fg_bucket")
    st.dataframe(
        overall.rename(columns={"fg_bucket":"bucket"})
               .style.format({
                   "avg_fwd1":"{:.4%}", "hit_fwd1":"{:.1%}",
                   "avg_fwd5":"{:.4%}", "hit_fwd5":"{:.1%}"
               }),
        use_container_width=True
    )

# download button
st.download_button(
    "Download bucket averages (CSV)",
    data=by_bucket.to_csv(index=False),
    file_name="bucket_averages_by_ticker.csv",
    mime="text/csv"
)

# --------- KPIs: average bounce per index ----------
st.markdown("### Average Forward Bounce by Index")
def kpi_table(df):
    if df.empty:
        return pd.DataFrame(columns=["ticker","avg_fwd1","hit_fwd1","avg_fwd5","hit_fwd5","count"])
    g = df.groupby("ticker")
    out = pd.DataFrame({
        "avg_fwd1": g["fwd1"].mean(),
        "hit_fwd1": g["fwd1"].apply(lambda s: (s > 0).mean()),
        "avg_fwd5": g["fwd5"].mean(),
        "hit_fwd5": g["fwd5"].apply(lambda s: (s > 0).mean()),
        "count": g["fwd1"].count()
    }).reset_index()
    return out

kpis = kpi_table(m.dropna(subset=["fwd1"]))
st.dataframe(kpis.style.format({
    "avg_fwd1": "{:.4%}", "hit_fwd1": "{:.1%}",
    "avg_fwd5": "{:.4%}", "hit_fwd5": "{:.1%}"
}), use_container_width=True)

# --------- Bars: avg fwd1/fwd5 by index (filtered bucket) ----------
col1, col2 = st.columns(2)
with col1:
    st.caption("Average 1-Day Forward Return")
    chart1 = (
        alt.Chart(kpis)
          .mark_bar()
          .encode(x=alt.X("ticker:N", title="Index"),
                  y=alt.Y("avg_fwd1:Q", title="Avg fwd1"),
                  tooltip=["ticker","avg_fwd1","hit_fwd1","count"])
          .properties(height=260)
    )
    st.altair_chart(chart1, use_container_width=True)

with col2:
    st.caption("Average 5-Day Forward Return")
    chart2 = (
        alt.Chart(kpis)
          .mark_bar()
          .encode(x=alt.X("ticker:N", title="Index"),
                  y=alt.Y("avg_fwd5:Q", title="Avg fwd5"),
                  tooltip=["ticker","avg_fwd5","hit_fwd5","count"])
          .properties(height=260)
    )
    st.altair_chart(chart2, use_container_width=True)

# --------- Optional: distribution viewer ----------
with st.expander("Return distribution (histogram)"):
    ret_window = st.radio("Forward window", ["fwd1","fwd5"], horizontal=True)
    if not m.empty:
        hist = (
            alt.Chart(m.dropna(subset=[ret_window]))
              .mark_bar()
              .encode(
                  x=alt.X(f"{ret_window}:Q", bin=alt.Bin(maxbins=50), title=f"{ret_window} return"),
                  y=alt.Y("count()", title="Count"),
                  color="ticker:N",
                  tooltip=[ret_window, "ticker", "count()"]
              )
              .properties(height=260)
        )
        st.altair_chart(hist, use_container_width=True)
    else:
        st.info("No rows after filters.")

# --------- Footers / notes ----------
st.markdown(
    """
    **Notes**
    - *Bucket filter* above drives the bounce stats and charts.  
    - *Date range* filters both the FG line and bounce stats.  
    - Downloads available in the sidebar.
    """
)
