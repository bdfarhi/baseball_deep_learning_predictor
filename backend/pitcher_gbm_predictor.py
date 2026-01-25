# backend/pitcher_gbm_predictor.py
import numpy as np
import joblib

from pitch_processing import compute_season_pitching, add_age

EPS = 1e-6
UPCOMING_YEAR = 2026
MIN_IP_FOR_HISTORY = 40

FEATURES = [
    "prev_logRA9",
    "prev_FIP",
    "prev_IP",
    "age_next",
    "prev_K9",
    "prev_BB9",
    "prev_HR9",
]

def safe_log(x):
    return np.log(np.clip(x, EPS, None))

def safe_exp(x):
    return np.exp(x)

def summarize_from_quantiles(p10, p50, p90):
    # simple interpolation for p25/p75
    p25 = p10 + 0.375 * (p50 - p10)
    p75 = p50 + 0.625 * (p90 - p50)
    mean = (p10 + 2*p50 + p90) / 4.0  # crude, stable
    return {
        "mean": float(mean),
        "p10": float(p10),
        "p25": float(p25),
        "p50": float(p50),
        "p75": float(p75),
        "p90": float(p90),
    }

class PitcherGBMPredictor:
    def __init__(self, people_df, season_pitching_df, models_dir="../models"):
        self.people = people_df
        self.season_pitching = season_pitching_df

        self.ra9_q10 = joblib.load(f"{models_dir}/pitch_gbm_logRA9_next_q10.joblib")
        self.ra9_q50 = joblib.load(f"{models_dir}/pitch_gbm_logRA9_next_q50.joblib")
        self.ra9_q90 = joblib.load(f"{models_dir}/pitch_gbm_logRA9_next_q90.joblib")

        self.fip_q10 = joblib.load(f"{models_dir}/pitch_gbm_FIP_next_q10.joblib")
        self.fip_q50 = joblib.load(f"{models_dir}/pitch_gbm_FIP_next_q50.joblib")
        self.fip_q90 = joblib.load(f"{models_dir}/pitch_gbm_FIP_next_q90.joblib")

    def get_player_id(self, full_name: str) -> str:
        first, last = full_name.split(" ", 1)
        row = self.people[(self.people["nameFirst"] == first) & (self.people["nameLast"] == last)]
        if row.empty:
            raise ValueError(f"No player found for name: {full_name}")
        return row.iloc[0]["playerID"]

    def _build_feature_row(self, playerID: str):
        hist = self.season_pitching[
            (self.season_pitching["playerID"] == playerID) &
            (self.season_pitching["yearID"] < UPCOMING_YEAR)
        ].sort_values("yearID")

        if hist.empty:
            raise ValueError("No pitching history found")

        hist_ip = hist[hist["IP"] >= MIN_IP_FOR_HISTORY]
        last = hist_ip.iloc[-1] if not hist_ip.empty else hist.iloc[-1]

        prev_year = int(last["yearID"])
        prev_ip  = float(last["IP"])
        prev_ra9 = float(last["RA9"])
        prev_fip = float(last["FIP_no_const"])
        prev_k9  = float(last["K9"])
        prev_bb9 = float(last["BB9"])
        prev_hr9 = float(last["HR9"])
        age_next = float(last["age"] + (UPCOMING_YEAR - prev_year))

        row = {
            "prev_logRA9": float(safe_log(max(prev_ra9, EPS))),
            "prev_FIP": prev_fip,
            "prev_IP": prev_ip,
            "age_next": age_next,
            "prev_K9": prev_k9,
            "prev_BB9": prev_bb9,
            "prev_HR9": prev_hr9,
        }
        return row, {
            "prev_year": prev_year,
            "prev_IP": prev_ip,
            "prev_RA9": prev_ra9,
            "prev_FIP_no_const": prev_fip,
            "age_next": age_next,
        }

    def predict(self, full_name: str):
        playerID = self.get_player_id(full_name)
        feat_row, cond_used = self._build_feature_row(playerID)

        X = np.array([[feat_row[c] for c in FEATURES]], dtype=np.float32)

        # Predict quantiles
        log_ra9_10 = float(self.ra9_q10.predict(X)[0])
        log_ra9_50 = float(self.ra9_q50.predict(X)[0])
        log_ra9_90 = float(self.ra9_q90.predict(X)[0])

        fip_10 = float(self.fip_q10.predict(X)[0])
        fip_50 = float(self.fip_q50.predict(X)[0])
        fip_90 = float(self.fip_q90.predict(X)[0])

        # Convert RA9 back from log-space
        ra9_10 = float(safe_exp(log_ra9_10))
        ra9_50 = float(safe_exp(log_ra9_50))
        ra9_90 = float(safe_exp(log_ra9_90))

        # clamp
        ra9_10, ra9_50, ra9_90 = [float(np.clip(v, 0.0, 20.0)) for v in (ra9_10, ra9_50, ra9_90)]
        fip_10, fip_50, fip_90 = [float(np.clip(v, -5.0, 20.0)) for v in (fip_10, fip_50, fip_90)]

        return {
            "name": full_name,
            "playerID": playerID,
            "upcoming_year": UPCOMING_YEAR,
            "condition_used": cond_used,
            "RA9": summarize_from_quantiles(ra9_10, ra9_50, ra9_90),
            "FIP_no_const": summarize_from_quantiles(fip_10, fip_50, fip_90),
        }
