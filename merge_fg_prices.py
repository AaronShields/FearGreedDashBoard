import pandas as pd
from pathlib import Path

FG_FILE     = Path("data/fg_history.csv")
PRICE_FILE  = Path("data/prices_2011_to_today.csv")
OUT_FILE    = Path("data/merged_fg_prices.csv")
BUCKET_STATS_FILE  = Path("data/fg_bucket_stats.csv")
MARKET_BUCKET_STATS_FILE = Path("data/fg_market_bucket_stats.csv")

# Buckets for FG
def fg_bucket(score):
    if score < 25: return "extreme fear"
    if score < 45: return "fear"
    if score < 55: return "neutral"
    if score < 75: return "greed"
    return "extreme greed"

def main():
    # Load Datasets
    fg = pd.read_csv(FG_FILE, parse_dates=["date"])
    prices = pd.read_csv(PRICE_FILE, parse_dates=["date"])

    # Clean FG Scores → integers
    fg["fg_score"] = (
        pd.to_numeric(fg["fg_score"], errors="coerce")
        .round()
        .astype("Int64")  # nullable integer
    )

    # Reassign bucket after rounding
    fg["fg_bucket"] = fg["fg_score"].apply(fg_bucket)

    # Merge sentiment + prices
    merged = pd.merge(
        prices,
        fg[["date","fg_score","fg_rating","fg_bucket"]],
        on="date",
        how="inner"
    ).sort_values(["ticker","date"]).reset_index(drop=True)

    # Compute forward 1-month return (≈ 20 trading days)
    merged["fwd20"] = merged.groupby("ticker")["close"].shift(-20)
    merged["fwd20"] = (merged["fwd20"] - merged["close"]) / merged["close"]

    # Reorder columns
    cols = [
        "date","ticker","close",
        "fg_score","fg_rating","fg_bucket",
        "ret1","fwd1","fwd5","fwd20"
    ]
    merged = merged[cols]

    # Save merged dataset
    merged.to_csv(OUT_FILE, index=False)
    print(f"✅ Saved merged dataset → {OUT_FILE} ({len(merged)} rows)")
    print("\n===== HEAD =====")
    print(merged.head(5).to_string(index=False))
    print("\n===== TAIL =====")
    print(merged.tail(5).to_string(index=False))

    # Summary: Average fwd20 by bucket
    summary = (
        merged.dropna(subset=["fwd20"])
              .groupby("fg_bucket")["fwd20"]
              .mean()
              .reset_index()
              .sort_values("fg_bucket")
    )

    print("\n===== Avg Forward 1-Month Return by Bucket =====")
    print(summary.to_string(index=False))

    # Classic bucket stats (all markets together)
    bucket_summary = (
        merged.dropna(subset=["fwd1","fwd5","fwd20"])
              .groupby("fg_bucket")
              .agg(
                  count=("fg_score", "count"),
                  avg_fwd1=("fwd1", "mean"),
                  avg_fwd5=("fwd5", "mean"),
                  avg_fwd20=("fwd20", "mean"),
                  std_fwd20=("fwd20", "std"),
                  min_fwd20=("fwd20", "min"),
                  max_fwd20=("fwd20", "max")
              )
              .reset_index()
              .sort_values("fg_bucket")
    )
    bucket_summary.to_csv(BUCKET_STATS_FILE, index=False)
    print("\n===== Bucket Summary Saved → data/fg_bucket_stats.csv =====")
    print(bucket_summary.to_string(index=False))

    # Market-by-bucket stats (per-market/ETF, per-bucket)
    market_bucket_summary = (
        merged.dropna(subset=["fwd1","fwd5","fwd20"])
              .groupby(["ticker", "fg_bucket"])
              .agg(
                  count=("fg_score", "count"),
                  avg_fwd1=("fwd1", "mean"),
                  avg_fwd5=("fwd5", "mean"),
                  avg_fwd20=("fwd20", "mean"),
                  std_fwd20=("fwd20", "std"),
                  min_fwd20=("fwd20", "min"),
                  max_fwd20=("fwd20", "max")
              )
              .reset_index()
              .sort_values(["ticker","fg_bucket"])
    )
    market_bucket_summary.to_csv(MARKET_BUCKET_STATS_FILE, index=False)
    print("\n===== Market-by-Bucket Stats Saved → data/fg_market_bucket_stats.csv =====")
    print(market_bucket_summary.to_string(index=False))

if __name__ == "__main__":
    main()
