import pandas as pd
import numpy as np

# ================================
# LOAD DATA
# ================================
df = pd.read_csv("data/merged_fg_prices.csv", parse_dates=["date"])
df = df.sort_values(["ticker", "date"]).reset_index(drop=True)

# ================================
# PARAMETERS
# ================================
WINDOW = 20  # local high window lookback

summary_rows = []
all_events = []

# ================================
# LOOP THROUGH EACH TICKER
# ================================
for ticker in df["ticker"].unique():

    d = df[df["ticker"] == ticker].copy().reset_index(drop=True)

    # ---------------------------
    # 1. Compute rolling highs
    # ---------------------------
    d["price_high"] = d["close"].rolling(WINDOW).max()
    d["fg_high"] = d["fg_score"].rolling(WINDOW).max()

    d["prev_price_high"] = d["price_high"].shift(1)
    d["prev_fg_high"] = d["fg_high"].shift(1)

    # ---------------------------
    # 2. Detect bearish divergence
    # ---------------------------
    d["price_higher_high"] = d["price_high"] > d["prev_price_high"]
    d["fg_lower_high"] = d["fg_high"] < d["prev_fg_high"]

    d["bearish_divergence"] = (
        d["price_higher_high"] & d["fg_lower_high"]
    ).astype(int)

    # Extract events
    events = d[d["bearish_divergence"] == 1].copy()
    events["ticker"] = ticker

    # Save events to combined list
    all_events.append(events)

    # ---------------------------
    # 3. Compute stats for this ticker
    # ---------------------------
    if len(events) > 0:
        summary_rows.append({
            "ticker": ticker,
            "count_divergences": len(events),
            "prob_down_fwd1":  (events["fwd1"] < 0).mean(),
            "prob_down_fwd5":  (events["fwd5"] < 0).mean(),
            "prob_down_fwd20": (events["fwd20"] < 0).mean(),
            "avg_fwd1":  events["fwd1"].mean(),
            "avg_fwd5":  events["fwd5"].mean(),
            "avg_fwd20": events["fwd20"].mean(),
            "median_fwd20": events["fwd20"].median(),
            "worst_fwd20":  events["fwd20"].min(),
            "best_fwd20":   events["fwd20"].max(),
        })
    else:
        summary_rows.append({
            "ticker": ticker,
            "count_divergences": 0,
            "prob_down_fwd1":  np.nan,
            "prob_down_fwd5":  np.nan,
            "prob_down_fwd20": np.nan,
            "avg_fwd1":  np.nan,
            "avg_fwd5":  np.nan,
            "avg_fwd20": np.nan,
            "median_fwd20": np.nan,
            "worst_fwd20":  np.nan,
            "best_fwd20":   np.nan,
        })

# ================================
# FINAL OUTPUT TABLES
# ================================
summary = pd.DataFrame(summary_rows)
events_all = pd.concat(all_events, ignore_index=True)

summary.to_csv("divergence_summary_by_ticker.csv", index=False)
events_all.to_csv("divergence_events_all_tickers.csv", index=False)

# Pretty print summary
print("\n===== BEARISH DIVERGENCE SUMMARY (PER TICKER) =====\n")
print(summary.to_string(index=False))

print("\nSaved detailed events → divergence_events_all_tickers.csv")
print("Saved summary → divergence_summary_by_ticker.csv")
