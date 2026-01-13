import numpy as np
import pandas as pd

EPS = 1e-6

def logit(p, eps=EPS):
    p = np.clip(p, eps, 1.0 - eps)
    return np.log(p / (1.0 - p))

def inv_logit(x):
    return 1.0 / (1.0 + np.exp(-x))

def safe_log(x, eps=EPS):
    return np.log(np.clip(x, eps, None))

def safe_exp(x):
    return np.exp(x)

def compute_season_obp_slg(batting_df):
    df = batting_df.copy()
    df = df[df["yearID"] >= 2000].copy()
    
    for col in ["AB", "H", "2B", "3B", "HR", "BB", "HBP", "SF"]:
        if col not in df.columns:
            df[col] = 0
    
    df[["AB", "H", "2B", "3B", "HR", "BB", "HBP", "SF"]] = df[["AB", "H", "2B", "3B", "HR", "BB", "HBP", "SF"]].fillna(0)
    df = df.groupby(["playerID", "yearID"], as_index=False)[["AB", "H", "2B", "3B", "HR", "BB", "HBP", "SF"]].sum()

    df["PA"] = df["AB"] + df["BB"] + df["HBP"] + df["SF"]
    df["1B"] = df["H"] - df["2B"] - df["3B"] - df["HR"]

    obp_den = (df["AB"] + df["BB"] + df["HBP"] + df["SF"]).replace(0, np.nan)
    slg_den = df["AB"].replace(0, np.nan)

    df["OBP"] = (df["H"] + df["BB"] + df["HBP"]) / obp_den
    df["SLG"] = (df["1B"] + 2 * df["2B"] + 3 * df["3B"] + 4 * df["HR"]) / slg_den

    df["OBP"] = df["OBP"].fillna(0.0).clip(0.0, 1.0)
    df["SLG"] = df["SLG"].fillna(0.0).clip(0.0, 2.0)

    return df[["playerID", "yearID", "PA", "OBP", "SLG"]]

def get_age_of_players(season, player_df):
    if "birthYear" not in player_df.columns:
        raise ValueError("Need 'birthYear' column")
    
    df = season.merge(player_df[["playerID", "birthYear"]].dropna(),
                     on="playerID", how="left")
    df["age"] = (df["yearID"] - df["birthYear"]).astype("float")
    df["age"] = df["age"].fillna(df["age"].median()).clip(15, 50)
    
    return df.drop(columns=["birthYear"])

class ZScaler:
    def fit(self, x):
        self.mu = x.mean(axis=0, keepdims=True)
        self.sig = x.std(axis=0, keepdims=True) + 1e-8
        return self
    
    def transform(self, x):
        return (x - self.mu) / self.sig
    
    def inv(self, x):
        return x * self.sig + self.mu