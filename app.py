import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Historical Fear & Greed Dashboard", layout="wide")

st.markdown("""
    <link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@700;900&family=Poppins:wght@400;600&display=swap" rel="stylesheet">
    <style>
        html, body, [class*="css"]  {
            font-family: 'Poppins', 'Montserrat', sans-serif !important;
        }
        .main-title {
            font-family: 'Montserrat', sans-serif !important;
            font-size: 2.6rem !important;
            letter-spacing: 0.01em;
        }
        .box-title {
            font-family: 'Montserrat', sans-serif !important;
            font-size: 2.0rem !important;
            font-weight: 900 !important;
            letter-spacing: 0.02em;
        }
        .box-value {
            font-family: 'Poppins', sans-serif !important;
            font-size: 2.2rem !important;
            font-weight: 700 !important;
        }
        .box-sub {
            font-size: 1.1rem !important;
            opacity: 0.87;
        }
    </style>
""", unsafe_allow_html=True)


# Loading merged dataset
fg = pd.read_csv("data/merged_fg_prices.csv", parse_dates=["date"])
bucket_stats = pd.read_csv("data/fg_bucket_stats.csv")

# Latest FG
fg_sorted = fg.sort_values("date")
latest = fg_sorted.iloc[-1]

current_date   = str(latest["date"].date())
current_score  = int(latest["fg_score"])
current_rating = latest["fg_bucket"]

RATING_COLOR = {
    "extreme fear": "#B22222",
    "fear": "#CC3333",
    "neutral": "#808080",
    "greed": "#2E8B57",
    "extreme greed": "#006400"
}

# Compute streak
days_in_streak = 1
for i in range(len(fg_sorted)-2, -1, -1):
    if fg_sorted.iloc[i]["fg_bucket"] == current_rating:
        days_in_streak += 1
    else:
        break

# Total days
total_days_for_bucket = int(
    bucket_stats.loc[bucket_stats["fg_bucket"] == current_rating, "count"].iloc[0]
)

# Header
st.title("Historical Fear & Greed Dashboard")
st.subheader("Daily Updates for Market Sentiment, Returns, and Historical Behavior")


# Columns
col1, col2, col3 = st.columns(3)

# Streak (Box 2)
with col1:
    st.markdown(
        f"""
    <div style="background-color:{RATING_COLOR[current_rating]};padding:40px;border-radius:22px;color:white;text-align:center;height:250px;display:flex;flex-direction:column;justify-content:center;">
        <div class="box-title">STREAK</div>
        <div class="box-value">{days_in_streak} days</div>
    </div>
    """, unsafe_allow_html=True
    )


# Current Market Sentiment
with col2:
    st.markdown(
        f"""
        <div style="background-color:{RATING_COLOR[current_rating]};padding:40px;border-radius:22px;color:white;text-align:center; height: 250px; display: flex; flex-direction: column; justify-content: center;">
            <div class="box-title">CURRENT SENTIMENT</div>
            <div class="box-value">{current_rating.upper()}</div>
            <div class="box-sub">{current_date} — Score: {current_score}</div>
        </div>
        """, unsafe_allow_html=True
)

# Total Days (Box 3)
with col3:
    st.markdown(
        f"""
    <div style="background-color:{RATING_COLOR[current_rating]};padding:40px;border-radius:22px;color:white;text-align:center;height:250px;display:flex;flex-direction:column;justify-content:center;">
        <div class="box-title">TOTAL DAYS</div>
        <div class="box-value">{total_days_for_bucket}</div>
        <div class="box-sub">(Historical)</div>
    </div>
    """, unsafe_allow_html=True
    )


cols = st.columns(2)
with cols[0]:
    selected_ticker = st.selectbox("Ticker", sorted(fg['ticker'].unique()), index=0)
with cols[1]:
    year_options = ["All"] + [str(y) for y in sorted(fg['date'].dt.year.unique())]
    selected_year = st.selectbox("Year", year_options, index=0)

data = fg[fg['ticker'] == selected_ticker]
if selected_year != "All":
    data = data[data['date'].dt.year == int(selected_year)]

min_date = data['date'].min().to_pydatetime()
max_date = data['date'].max().to_pydatetime()
date_range = st.slider(
    "Zoom to Date Range",
    min_value=min_date,
    max_value=max_date,
    value=(min_date, max_date)
)
data = data[(data['date'] >= pd.to_datetime(date_range[0])) & (data['date'] <= pd.to_datetime(date_range[1]))]

bucket_colors = {
    "extreme fear": "#8B0000",
    "fear": "#CC3333",
    "neutral": "#808080",
    "greed": "#2E8B57",
    "extreme greed": "#006400"
}


fig = go.Figure()

fig.add_trace(
    go.Scatter(
        x=data['date'],
        y=data['close'],
        name=f"{selected_ticker} Price",
        yaxis="y1",
        mode="lines",
        line=dict(color="white", width=2, dash="solid"),
        opacity=0.6
    )
)

fig.add_trace(
    go.Scatter(
        x=data['date'],
        y=data['fg_score'],
        mode="lines",             
        name="Fear & Greed Score",
        line=dict(color="#CCCCCC", width=1.5),  
        opacity=0.25,                
        yaxis="y2"
    )
)


fig.update_layout(
    template="plotly_dark",
    yaxis=dict(title="Price (USD)", side="left"),
    yaxis2=dict(
        title="Fear & Greed Score",
        overlaying="y",
        side="right",
        range=[0, 100]
    ),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
)

st.plotly_chart(fig, use_container_width=True)

# market bucket stats
market_bucket_stats = pd.read_csv("data/fg_market_bucket_stats.csv")

return_window = st.radio(
    f"Select Forward Return Window For Current Sentiment: {current_rating.title()}",
    ['avg_fwd1', 'avg_fwd5', 'avg_fwd20'],
    horizontal=True
)

# Display Boxes
cols = st.columns(3)
for i, ticker in enumerate(["DIA", "SPY", "QQQ"]):
    sub = market_bucket_stats[market_bucket_stats['ticker'] == ticker]
    if not sub.empty:
        avg_return = sub[return_window].values[0] * 100  # to percentage
        label = return_window.split('_')[1]  # 'fwd1', 'fwd5', or 'fwd20' → '1', '5', '20'
        with cols[i]:
            st.markdown(f"""
                <div style="background-color:#222; border-radius:16px; padding:30px; text-align:center;">
                    <div style="font-size:20px; font-weight:bold;">{ticker}</div>
                    <div style="font-size:28px; color:#50fa7b; font-weight:700;">{avg_return:.2f}%</div>
                    <div style="font-size:14px; opacity:0.7;">Forward Return {label} day{'s' if label != '1' else ''}</div>
                </div>
            """, unsafe_allow_html=True)
    else:
        with cols[i]:
            st.write(f"No data for {ticker}")
