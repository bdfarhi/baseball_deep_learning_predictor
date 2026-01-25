# backend/train_pitch_quantiles.py
import os
import numpy as np
import pandas as pd
import joblib

from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error

from pitch_processing import compute_season_pitching, add_age

# ------------------
# Config
# ------------------
UPCOMING_YEAR = 2026
TRAIN_END_YEAR = 2024
VAL_YEAR = 2025
EXCLUDE_YEAR = 2020

# "Full-time" for UI filtering uses your single threshold later.
# For training pairs, use a smaller threshold so you have enough data:
MIN_IP_TRAIN = 60

QUANTILES = [0.10, 0.50, 0.90]

# Features (suggested)
FEATURES = [
    "prev_logRA9",
    "prev_FIP",
    "prev_IP",
    "age_next",
    "prev_K9",
    "prev_BB9",
    "prev_HR9",
]

TARGETS = ["logRA9_next", "FIP_next"]  # we model log(RA9) and raw FIP

def safe_log(x, eps=1e-6):
    return np.log(np.clip(x, eps, None))

def make_training_pairs(season: pd.DataFrame) -> pd.DataFrame:
    df = season.sort_values(["playerID", "yearID"]).copy()

    # previous season values
    df["prev_year"] = df.groupby("playerID")["yearID"].shift(1)
    df["prev_RA9"]  = df.groupby("playerID")["RA9"].shift(1)
    df["prev_FIP"]  = df.groupby("playerID")["FIP_no_const"].shift(1)
    df["prev_IP"]   = df.groupby("playerID")["IP"].shift(1)
    df["prev_K9"]   = df.groupby("playerID")["K9"].shift(1)
    df["prev_BB9"]  = df.groupby("playerID")["BB9"].shift(1)
    df["prev_HR9"]  = df.groupby("playerID")["HR9"].shift(1)
    df["prev_age"]  = df.groupby("playerID")["age"].shift(1)

    out = df.dropna(subset=[
        "prev_year","prev_RA9","prev_FIP","prev_IP","prev_K9","prev_BB9","prev_HR9","prev_age"
    ]).copy()

    # require consecutive seasons
    out = out[out["prev_year"] == out["yearID"] - 1].copy()

    # training eligibility
    out = out[(out["IP"] >= MIN_IP_TRAIN) & (out["prev_IP"] >= MIN_IP_TRAIN)].copy()

    # features
    out["prev_logRA9"] = safe_log(np.maximum(out["prev_RA9"].to_numpy(), 1e-6))
    out["age_next"] = out["prev_age"] + 1.0  # if consecutive year, next age ≈ prev_age + 1

    # targets
    out["logRA9_next"] = safe_log(np.maximum(out["RA9"].to_numpy(), 1e-6))
    out["FIP_next"] = out["FIP_no_const"]

    return out

def train_quantile_model(X_train, y_train, q: float) -> GradientBoostingRegressor:
    # Strong baseline settings; you can tune later
    model = GradientBoostingRegressor(
        loss="quantile",
        alpha=q,
        n_estimators=600,
        learning_rate=0.05,
        max_depth=3,
        subsample=0.8,
        random_state=42,
    )
    model.fit(X_train, y_train)
    return model

def main():
    os.makedirs("../models", exist_ok=True)

    pitching = pd.read_csv("../data/Pitching.csv")
    people   = pd.read_csv("../data/People.csv")

    season = compute_season_pitching(pitching)
    season = add_age(season, people)

    pairs = make_training_pairs(season)

    # time split by target year
    train_df = pairs[(pairs["yearID"] <= TRAIN_END_YEAR) & (pairs["yearID"] != EXCLUDE_YEAR)].copy()
    val_df   = pairs[pairs["yearID"] == VAL_YEAR].copy()

    if train_df.empty:
        raise RuntimeError("No training rows produced. Check MIN_IP_TRAIN and year filtering.")

    X_train = train_df[FEATURES].to_numpy(np.float32)
    X_val   = val_df[FEATURES].to_numpy(np.float32) if len(val_df) else None

    print(f"Train rows: {len(train_df)} | Val rows: {len(val_df)}")
    print("Features:", FEATURES)

    # Train 2 targets * 3 quantiles
    for target in TARGETS:
        y_train = train_df[target].to_numpy(np.float32)
        y_val = val_df[target].to_numpy(np.float32) if len(val_df) else None

        for q in QUANTILES:
            print(f"\nTraining {target} @ q={q:.2f}")
            model = train_quantile_model(X_train, y_train, q)

            # quick eval: MAE on val if available
            if X_val is not None and y_val is not None and len(val_df):
                pred = model.predict(X_val)
                mae = mean_absolute_error(y_val, pred)
                print(f"  Val MAE: {mae:.4f}")
            else:
                print("  No val set found (VAL_YEAR missing).")

            out_path = f"../models/pitch_gbm_{target}_q{int(q*100):02d}.joblib"
            joblib.dump(model, out_path)
            print(f"  Saved -> {out_path}")

    print("\nDone! Pitch quantile GBM models saved in /models")

if __name__ == "__main__":
    main()
