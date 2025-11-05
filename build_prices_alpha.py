from __future__ import annotations
import os, time
from pathlib import Path
from typing import Iterable, List
import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()

ALPHA_URL   = "https://www.alphavantage.co/query"
API_KEY     = os.getenv("ALPHAVANTAGE_API_KEY")
START_DATE  = "2011-01-01"
END_DATE    = None
CALLS_PER_MIN = 5
RETRIES     = 2

OUT_DIR     = Path("data")
OUT_DIR.mkdir(parents=True, exist_ok=True)
COMBINED_CSV = OUT_DIR / "prices_2011_to_today.csv"

def _alpha_request(params: dict) -> dict:
    r = requests.get(ALPHA_URL, params=params, timeout=30)
    r.raise_for_status()
    return r.json()

def _parse_alpha(ts: dict, ticker: str) -> pd.DataFrame:
    df = pd.DataFrame.from_dict(ts, orient="index")
    df.index = pd.to_datetime(df.index)
    # prefer adjusted close if present; else use close
    col = "5. adjusted close" if "5. adjusted close" in df.columns else "4. close"
    df = df.rename(columns={col: "close"})
    df = df[["close"]].astype(float).sort_index().reset_index().rename(columns={"index": "date"})
    df["ticker"] = ticker.upper()
    return df[["date", "ticker", "close"]]

def fetch_alpha(ticker: str, api_key: str) -> pd.DataFrame | None:
    """Try adjusted first, then non-adjusted. Return None if both fail."""
    for attempt in range(1, RETRIES + 1):
        # 1) adjusted
        params = {
            "function": "TIME_SERIES_DAILY_ADJUSTED",
            "symbol": ticker,
            "outputsize": "full",
            "datatype": "json",
            "apikey": api_key,
        }
        js = _alpha_request(params)
        if "Time Series (Daily)" in js:
            return _parse_alpha(js["Time Series (Daily)"], ticker)
        # if premium/rate-limit Note, try non-adjusted next
        # 2) non-adjusted
        params["function"] = "TIME_SERIES_DAILY"
        js2 = _alpha_request(params)
        if "Time Series (Daily)" in js2:
            return _parse_alpha(js2["Time Series (Daily)"], ticker)
        # if rate limited, backoff and retry
        if "Note" in js or "Note" in js2:
            time.sleep(60.0 / max(CALLS_PER_MIN, 1) + 2)
            continue
        # if real error message, stop trying AV
        if "Error Message" in js2 or "Error Message" in js:
            break
        break
    return None

def fetch_yfinance(ticker: str, start: str | None, end: str | None) -> pd.DataFrame:
    import yfinance as yf
    df = yf.download(ticker, start=start, end=end, auto_adjust=True, progress=False)
    if df.empty:
        raise RuntimeError(f"yfinance returned no data for {ticker}")
    df = df.reset_index().rename(columns={"Date": "date", "Adj Close": "close"})
    # some regions label "Adj Close" differently; fall back if needed
    if "close" not in df.columns and "Close" in df.columns:
        df = df.rename(columns={"Close": "close"})
    df["ticker"] = ticker.upper()
    return df[["date", "ticker", "close"]]

def load_prices_once(
    tickers: Iterable[str],
    api_key: str | None,
    start: str | None = START_DATE,
    end: str | None = END_DATE,
) -> pd.DataFrame:
    results: List[pd.DataFrame] = []
    for i, t in enumerate([t.upper() for t in tickers]):
        if i > 0:
            time.sleep(60.0 / max(CALLS_PER_MIN, 1))  # be gentle between symbols

        # Try Alpha if key present, else fallback to yfinance
        df = fetch_alpha(t, api_key) if api_key else None
        if df is None:
            df = fetch_yfinance(t, start=start, end=end)

        # ensure datetime for consistent filtering
        df["date"] = pd.to_datetime(df["date"])

        # date filter (yfinance usually honors already; AV needs it)
        if start:
            df = df[df["date"] >= pd.to_datetime(start)]
        if end:
            df = df[df["date"] <= pd.to_datetime(end)]

        results.append(df)

    out = (
        pd.concat(results, ignore_index=True)
          .drop_duplicates(subset=["ticker", "date"])  # safety
          .sort_values(["ticker", "date"])
          .reset_index(drop=True)
    )
    return out


def add_returns(df: pd.DataFrame, horizons=(1, 5)) -> pd.DataFrame:
    """
    Adds:
      ret1  : close(t)/close(t-1) - 1
      fwdH  : close(t+H)/close(t) - 1
    Uses groupby+shift so indices align with the original rows.
    """
    out = df.sort_values(["ticker", "date"]).reset_index(drop=True).copy()

    # backward daily return
    out["ret1"] = out.groupby("ticker")["close"].pct_change(1)

    # forward returns without MultiIndex
    for h in horizons:
        future_close = out.groupby("ticker")["close"].shift(-h)
        out[f"fwd{h}"] = (future_close / out["close"]) - 1

    return out


if __name__ == "__main__":
    # choose your “major markets”
    tickers = ["SPY", "QQQ", "DIA"]  # add "IWM" if you want small-caps too

    prices = load_prices_once(
        tickers=tickers,
        api_key=API_KEY,           # may be None; yfinance will be used
        start=START_DATE,
        end=END_DATE,
    )
    prices = add_returns(prices, horizons=(1,5))
    prices.to_csv(COMBINED_CSV, index=False)
    print(f"✅ Saved combined CSV → {COMBINED_CSV}  rows={len(prices)}")
    print(prices.groupby("ticker").tail(2).to_string(index=False))
