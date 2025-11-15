import pandas as pd

def rating_from_score(score):
    if score is None or pd.isna(score):
        return ""
    score = float(score)
    if score <= 25:
        return "extreme fear"
    elif score <= 45:
        return "fear"
    elif score <= 55:
        return "neutral"
    elif score <= 75:
        return "greed"
    else:
        return "extreme greed"

df = pd.read_csv("2024_manual.csv")
df["fg_rating"] = df["fg_score"].apply(rating_from_score)
df.to_csv("2024_manual_filled.csv", index=False)