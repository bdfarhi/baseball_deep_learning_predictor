import pandas as pd
import numpy as np
import pickle
from data_processing import compute_season_obp_slg, get_age_of_players, ZScaler, logit, safe_log

# Load data
batting = pd.read_csv('../data/Batting.csv')
people = pd.read_csv('../data/People.csv')

# Process data
season_stats = compute_season_obp_slg(batting)
season_stats = get_age_of_players(season_stats, people)

# Create conditional data
def make_conditional(data, min_pa=400, require_consecutive=True):
    df = data.sort_values(["playerID", "yearID"]).copy()
    
    df["prev_OBP"] = df.groupby("playerID")["OBP"].shift(1)
    df["prev_SLG"] = df.groupby("playerID")["SLG"].shift(1)
    df["prev_PA"] = df.groupby("playerID")["PA"].shift(1)
    df["prev_year"] = df.groupby("playerID")["yearID"].shift(1)
    
    out = df.dropna(subset=["prev_OBP", "prev_SLG", "prev_PA", "prev_year"]).copy()
    
    if require_consecutive:
        out = out[out["prev_year"] == out["yearID"] - 1].copy()
    
    out = out[(out["PA"] >= min_pa) & (out["prev_PA"] >= min_pa)].copy()
    
    return out

# Add transformed columns
def add_transformed_columns(df):
    df = df.copy()
    df["zOBP"] = logit(df["OBP"].to_numpy())
    df["prev_zOBP"] = logit(df["prev_OBP"].to_numpy())
    df["logSLG"] = safe_log(df["SLG"].to_numpy())
    df["prev_logSLG"] = safe_log(df["prev_SLG"].to_numpy())
    df["d_zOBP"] = df["zOBP"] - df["prev_zOBP"]
    df["d_logSLG"] = df["logSLG"] - df["prev_logSLG"]
    return df

# Create training data
cond_all = make_conditional(season_stats, min_pa=400, require_consecutive=True)
TRAIN_END_YEAR = 2024
EXCLUDE_YEAR = 2020

train_df = cond_all[
    (cond_all["yearID"] <= TRAIN_END_YEAR) & 
    (cond_all["yearID"] != EXCLUDE_YEAR)
].copy()

train_df = add_transformed_columns(train_df)

# Fit and save scalers
cond_cols = ["prev_zOBP", "prev_logSLG", "prev_PA", "age"]
y_cols = ["d_zOBP", "d_logSLG"]

cond_scaler = ZScaler().fit(train_df[cond_cols].to_numpy(np.float32))
y_scaler = ZScaler().fit(train_df[y_cols].to_numpy(np.float32))

# Save scalers
with open('../models/cond_scaler.pkl', 'wb') as f:
    pickle.dump(cond_scaler, f)

with open('../models/y_scaler.pkl', 'wb') as f:
    pickle.dump(y_scaler, f)

print("Scalers saved successfully!")