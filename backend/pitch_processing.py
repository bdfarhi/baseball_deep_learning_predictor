# backend/pitch_processing.py
import numpy as np
import pandas as pd

def safe_div(num, den):
    den = np.where(den == 0, np.nan, den)
    return num / den

def compute_season_pitching(pitching_df: pd.DataFrame) -> pd.DataFrame:
    df = pitching_df.copy()
    df = df[df["yearID"] >= 2000].copy()

    needed = ["IPouts", "R", "ER", "SO", "BB", "HR"]
    for c in needed:
        if c not in df.columns:
            df[c] = 0
    if "HBP" not in df.columns:
        df["HBP"] = 0

    df[needed + ["HBP"]] = df[needed + ["HBP"]].fillna(0)

    df = df.groupby(["playerID", "yearID"], as_index=False)[needed + ["HBP"]].sum()

    df["IP"] = df["IPouts"] / 3.0
    ip = df["IP"].to_numpy()

    df["RA9"] = 9.0 * safe_div(df["R"].to_numpy(), ip)
    df["ERA"] = 9.0 * safe_div(df["ER"].to_numpy(), ip)
    df["K9"]  = 9.0 * safe_div(df["SO"].to_numpy(), ip)
    df["BB9"] = 9.0 * safe_div(df["BB"].to_numpy(), ip)
    df["HR9"] = 9.0 * safe_div(df["HR"].to_numpy(), ip)

    # FIP without constant: (13*HR + 3*(BB+HBP) - 2*SO) / IP
    df["FIP_no_const"] = safe_div(
        (13.0 * df["HR"] + 3.0 * (df["BB"] + df["HBP"]) - 2.0 * df["SO"]).to_numpy(),
        ip
    )

    # clean
    for col in ["RA9", "ERA", "K9", "BB9", "HR9", "FIP_no_const"]:
        df[col] = df[col].replace([np.inf, -np.inf], np.nan).fillna(0.0)

    df["RA9"] = df["RA9"].clip(0.0, 20.0)
    df["FIP_no_const"] = df["FIP_no_const"].clip(-5.0, 20.0)
    df["IP"] = df["IP"].clip(0.0, 300.0)

    return df[["playerID","yearID","IP","R","ER","SO","BB","HR","HBP",
               "RA9","ERA","K9","BB9","HR9","FIP_no_const"]]

def add_age(season_df: pd.DataFrame, people_df: pd.DataFrame) -> pd.DataFrame:
    if "birthYear" not in people_df.columns:
        raise ValueError("People.csv needs birthYear")

    out = season_df.merge(
        people_df[["playerID","birthYear"]].dropna(),
        on="playerID",
        how="left"
    )
    out["age"] = (out["yearID"] - out["birthYear"]).astype("float")
    out["age"] = out["age"].fillna(out["age"].median()).clip(15, 50)
    return out.drop(columns=["birthYear"])
