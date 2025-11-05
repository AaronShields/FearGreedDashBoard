# build_fg_history_base.py
import pandas as pd
from pathlib import Path

# Raw CSV covering 2011–2023
BASE_2011_2023 = (
    "https://raw.githubusercontent.com/whit3rabbit/fear-greed-data/main/"
    "fear-greed-2011-2023.csv"
)

OUT = Path("data")
HIST = OUT / "fg_history.csv"

alpha_vantage_API = 'MCX5T9JI4BFJJ98H'

def classify_rating(score: float) -> str: 
    if pd.isna(score):
        return None
    if score < 25:
        return "extreme fear"
    if score < 45: 
        return "fear"
    if score < 55: 
        return "neutral"
    if score < 75: 
        return "greed"
    return "extreme greed"

def main():
    OUT.mkdir(parents=True, exist_ok=True)

    # Load base CSV
    df = pd.read_csv(BASE_2011_2023)
    df = df.rename(columns={"Date": "date", "Fear Greed": "fg_score"})
    df["date"] = pd.to_datetime(df["date"]).dt.date

    # Get score and assign rating 
    df["fg_score"] = pd.to_numeric(df["fg_score"], errors="coerce")
    df["fg_rating"] = df["fg_score"].apply(classify_rating)

    # Sort and write
    df = df[["date", "fg_score", "fg_rating"]].sort_values("date").reset_index(drop=True)
    df.to_csv(HIST, index=False)

    print(f"✅ Saved history → {HIST} (rows={len(df)})")
    print(df.head(3).to_string(index=False))
    print(df.tail(3).to_string(index=False))

if __name__ == "__main__":
    main()
