import pandas as pd
from pathlib import Path

FG_FILE     = Path("data/fg_history.csv")
PRICE_FILE  = Path("data/prices_2011_to_today.csv")
OUT_FILE    = Path("data/merged_fg_prices.csv")

# consistent bucketing
def fg_bucket(score):
    if score < 25: return "extreme fear"
    if score < 45: return "fear"
    if score < 55: return "neutral"
    if score < 75: return "greed"
    return "extreme greed"

def main():
    fg = pd.read_csv(FG_FILE, parse_dates=["date"])
    prices = pd.read_csv(PRICE_FILE, parse_dates=["date"])

    # merge on date
    merged = pd.merge(
        prices, fg,
        on="date",
        how="inner"          # only days we have both sentiment and prices
    )

    merged["fg_bucket"] = merged["fg_score"].apply(fg_bucket)

    # reorder columns
    cols = ["date","ticker","close","fg_score","fg_rating","fg_bucket","ret1","fwd1","fwd5"]
    merged = merged[cols].sort_values(["ticker","date"]).reset_index(drop=True)

    merged.to_csv(OUT_FILE, index=False)
    print(f"✅ Saved merged dataset → {OUT_FILE} (rows={len(merged)})")
    print(merged.head(5).to_string(index=False))
    print(merged.tail(5).to_string(index=False))

if __name__ == "__main__":
    main()
