import requests
import pandas as pd

URL = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_0_0)",
    "Accept": "application/json",
    "Connection": "keep-alive"
}

def cnn_timestamp_to_market_date(x):
    dt_utc = pd.to_datetime(x, unit='ms', utc=True)
    dt_est = dt_utc.tz_convert("America/New_York")
    d = pd.Timestamp(dt_est.date())

    # Shift if weekend
    if d.weekday() == 5:   # Saturday
        d -= pd.Timedelta(days=1)
    elif d.weekday() == 6: # Sunday
        d -= pd.Timedelta(days=2)

    return d.strftime("%Y-%m-%d")

def score_to_bucket(x):
    if x < 25: return "extreme fear"
    if x < 45: return "fear"
    if x < 55: return "neutral"
    if x < 75: return "greed"
    return "extreme greed"

def fetch_cnn_fear_greed():
    print("Fetching CNN Fear & Greed JSON…")
    r = requests.get(URL, headers=HEADERS, timeout=20)
    r.raise_for_status()

    data = r.json()

    print("TOP LEVEL KEYS:", list(data.keys()))
    print("fear_and_greed TYPE:", type(data.get("fear_and_greed")))
    print("fear_and_greed VALUE (first 300 chars):", str(data.get("fear_and_greed"))[:300])

    print("fear_and_greed_historical TYPE:", type(data.get("fear_and_greed_historical")))
    print("fear_and_greed_historical VALUE (first 300 chars):", str(data.get("fear_and_greed_historical"))[:300])

    exit()

def rebuild():
    print("Fetching CNN Fear & Greed JSON…")
    r = requests.get(URL, headers=HEADERS, timeout=20)
    r.raise_for_status()
    data = r.json()

    hist = data["fear_and_greed_historical"]["data"]

    rows = []
    for entry in hist:
        ts = entry["x"]
        score = entry["y"]
        mkt_date = cnn_timestamp_to_market_date(ts)
        rows.append((mkt_date, score))

    df = pd.DataFrame(rows, columns=["date", "fg_score"])
    df = df.drop_duplicates(subset=["date"])
    df = df.sort_values("date").reset_index(drop=True)
    df["fg_rating"] = df["fg_score"].apply(score_to_bucket)

    df["weekday"] = pd.to_datetime(df["date"]).dt.weekday
    df = df[df["weekday"] < 5].drop(columns=["weekday"])

    # WRITE TO A DIFFERENT FILE
    output_file = "fg_history_rebuilt.csv"
    df.to_csv(output_file, index=False)

    print(f"✔ Rebuild complete: {output_file} written")
    print(df.head())
    print(df.tail())


if __name__ == "__main__":
    rebuild()
