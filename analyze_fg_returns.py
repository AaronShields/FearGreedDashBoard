import pandas as pd
from pathlib import Path
import numpy as np

MERGED = Path("data/merged_fg_prices.csv")
OUT_DIR = Path("data/analysis")
OUT_DIR.mkdir(parents=True, exist_ok=True)

def main():
    df = pd.read_csv(MERGED, parse_dates=["date"])
    df = df.dropna(subset=["fwd1", "fg_score"])  

    # Correlations
    pearson_fwd1 = df["fg_score"].corr(df["fwd1"])
    pearson_fwd5 = df["fg_score"].corr(df["fwd5"])
    
    # Spearman
    try:
        spearman_fwd1 = df["fg_score"].corr(df["fwd1"], method="spearman")
        spearman_fwd5 = df["fg_score"].corr(df["fwd5"], method="spearman")
    except Exception:
        spearman_fwd1, spearman_fwd5 = np.nan, np.nan

    corr_df = pd.DataFrame([
        {"metric": "pearson_fwd1", "value": pearson_fwd1},
        {"metric": "pearson_fwd5", "value": pearson_fwd5},
        {"metric": "spearman_fwd1", "value": spearman_fwd1},
        {"metric": "spearman_fwd5", "value": spearman_fwd5},
    ])
    corr_fp = OUT_DIR / "correlation_summary.csv"
    corr_df.to_csv(corr_fp, index=False)
    print(f" Saved correlations → {corr_fp}")

    # Bucket summary (1-day)
    summary1 = (
        df
        .groupby(["fg_bucket", "ticker"])
        .agg(
            avg_fwd1=("fwd1","mean"),
            med_fwd1=("fwd1","median"),
            hit_fwd1=("fwd1", lambda s: (s > 0).mean()),
            std_fwd1=("fwd1","std"),
            count=("fwd1","count"),
        )
        .reset_index()
        .sort_values(["fg_bucket","avg_fwd1"], ascending=[True,False])
    )
    fwd1_fp = OUT_DIR / "bucket_performance_fwd1.csv"
    summary1.to_csv(fwd1_fp, index=False)
    print(f"1-day bucket summary → {fwd1_fp}")

    # Best by Bucket Summary
    best_by_bucket = (
        summary1
        .groupby("fg_bucket")
        .apply(lambda g: g.sort_values("avg_fwd1", ascending=False).head(1))
        .reset_index(drop=True)
    )
    best_fp = OUT_DIR / "best_per_bucket.csv"
    best_by_bucket.to_csv(best_fp, index=False)
    print(f"Saved best index per bucket → {best_fp}")

    # 5-day summary
    df5 = df.dropna(subset=["fwd5"])
    summary5 = (
        df5
        .groupby(["fg_bucket","ticker"])
        .agg(
            avg_fwd5=("fwd5","mean"),
            med_fwd5=("fwd5","median"),
            hit_fwd5=("fwd5", lambda s: (s > 0).mean()),
            std_fwd5=("fwd5","std"),
            count=("fwd5","count"),
        )
        .reset_index()
        .sort_values(["fg_bucket","avg_fwd5"], ascending=[True,False])
    )
    fwd5_fp = OUT_DIR / "bucket_performance_fwd5.csv"
    summary5.to_csv(fwd5_fp, index=False)
    print(f" Saved 5-day bucket summary → {fwd5_fp}")

    # Script Finish
    print("\n--- OUTPUT COMPLETE ---")
    print(f"Correlations:           {corr_fp}")
    print(f"1-day bucket summary:   {fwd1_fp}")
    print(f"Best index per bucket:  {best_fp}")
    print(f"5-day bucket summary:   {fwd5_fp}")

if __name__ == "__main__":
    main()
