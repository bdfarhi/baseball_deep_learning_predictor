import numpy as np
import pandas as pd

PYTHAG_EXP = 1.83          # common MLB pythag exponent
GAMES = 162
DEFAULT_N_SIMS = 1500      # for wins distribution

def _sigma_from_p10_p90(p10, p90):
    # for a Normal: P90 - P10 ≈ 2.563 * sigma
    return max((p90 - p10) / 2.563, 1e-6)

def _sample_from_quantiles(q, n):
    # q is dict: mean, p10, p25, p50, p75, p90
    mu = float(q["mean"])
    sig = _sigma_from_p10_p90(float(q["p10"]), float(q["p90"]))
    return np.random.normal(mu, sig, size=n)

def _pythag_wins(rs_per_g, ra_per_g, games=GAMES, exp=PYTHAG_EXP):
    rs = np.clip(rs_per_g, 0.01, None)
    ra = np.clip(ra_per_g, 0.01, None)
    wp = (rs ** exp) / ((rs ** exp) + (ra ** exp))
    return games * wp

def compute_team_ops_from_batting(batting_df):
    """
    Team OPS by (teamID, yearID) from Lahman Batting.csv.
    """
    df = batting_df.copy()
    keep = ["teamID", "yearID", "AB", "H", "2B", "3B", "HR", "BB", "HBP", "SF"]
    for c in keep:
        if c not in df.columns:
            df[c] = 0
    df[keep] = df[keep].fillna(0)

    grp = df.groupby(["teamID", "yearID"], as_index=False)[["AB","H","2B","3B","HR","BB","HBP","SF"]].sum()
    grp["1B"] = grp["H"] - grp["2B"] - grp["3B"] - grp["HR"]
    grp["PA"] = grp["AB"] + grp["BB"] + grp["HBP"] + grp["SF"]

    obp_den = (grp["AB"] + grp["BB"] + grp["HBP"] + grp["SF"]).replace(0, np.nan)
    slg_den = grp["AB"].replace(0, np.nan)

    grp["OBP"] = (grp["H"] + grp["BB"] + grp["HBP"]) / obp_den
    grp["SLG"] = (grp["1B"] + 2*grp["2B"] + 3*grp["3B"] + 4*grp["HR"]) / slg_den
    grp["OPS"] = grp["OBP"].fillna(0) + grp["SLG"].fillna(0)

    return grp[["teamID", "yearID", "OPS"]]

def compute_team_runs_allowed_per_game(teams_df):
    """
    Teams.csv has team runs allowed (RA) and games (G) for many seasons.
    """
    df = teams_df.copy()
    df = df.dropna(subset=["RA", "G"])
    df["RA_per_G"] = df["RA"] / df["G"]
    return df[["teamID", "yearID", "RA_per_G"]]

def fit_linear(x, y):
    """
    y ≈ a*x + b using numpy least squares (no sklearn needed).
    """
    x = np.asarray(x).reshape(-1, 1)
    y = np.asarray(y).reshape(-1, 1)
    X = np.hstack([x, np.ones((x.shape[0], 1))])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    a = float(beta[0, 0])
    b = float(beta[1, 0])
    return a, b

class TeamWinsPredictor:
    """
    Uses:
      - hitter_predictor: returns OBP/SLG/OPS quantiles
      - pitcher_predictor: returns RA9 quantiles (recommended) + maybe FIP
    Produces:
      - wins distribution + summary
    """
    def __init__(self, hitter_predictor, pitcher_predictor, batting_df, teams_df):
        self.hitter_predictor = hitter_predictor
        self.pitcher_predictor = pitcher_predictor

        # Fit RS/G from Team OPS using historical seasons
        team_ops = compute_team_ops_from_batting(batting_df)
        teams = teams_df.copy()

        # Teams.csv has R and G -> RS/G
        teams = teams.dropna(subset=["R", "G"])
        teams["RS_per_G"] = teams["R"] / teams["G"]

        merged = teams.merge(team_ops, on=["teamID","yearID"], how="inner").dropna(subset=["OPS","RS_per_G"])
        if len(merged) < 100:
            # fallback constants if the dataset merge is somehow small
            self.rs_a, self.rs_b = (5.0, 0.0)  # coarse fallback
        else:
            self.rs_a, self.rs_b = fit_linear(merged["OPS"].values, merged["RS_per_G"].values)

        # Fit RA/G from team RA/G baseline (we’ll still mainly use pitcher RA9)
        ra_df = compute_team_runs_allowed_per_game(teams_df).dropna()
        self.league_ra_per_g = float(ra_df["RA_per_G"].mean()) if len(ra_df) else 4.5

        # starter/bullpen split assumption (simple + effective)
        self.starter_innings = 6.0
        self.bullpen_innings = 3.0
        self.bullpen_ra9 = self.league_ra_per_g  * 1.05   # approximate bullpen level

    def roster_to_ops_samples(self, hitters, n_sims):
        """
        hitters = list[str] (9 hitters + DH)
        returns array of team OPS samples
        """
        ops_samples = []
        for name in hitters:
            pred = self.hitter_predictor.predict(name)
            ops_q = pred["OPS"]
            ops_samples.append(_sample_from_quantiles(ops_q, n_sims))
        ops_samples = np.vstack(ops_samples)  # shape (N_hitters, n_sims)
        # Simple equal-weight average
        return ops_samples.mean(axis=0)

    def rotation_to_ra9_samples(self, starters, n_sims):
        """
        starters = list[str] of 5 names
        returns array of starter RA9 samples averaged over rotation
        """
        ra9_samples = []
        for name in starters:
            pred = self.pitcher_predictor.predict(name)
            # expect your pitcher predictor to return "RA9" quantiles
            ra9_q = pred.get("RA9") or pred.get("RA9_next") or pred.get("RA9_proj")
            if ra9_q is None:
                raise ValueError("Pitcher predictor must return RA9 quantiles (key 'RA9').")
            ra9_samples.append(_sample_from_quantiles(ra9_q, n_sims))

        ra9_samples = np.vstack(ra9_samples)
        return ra9_samples.mean(axis=0)

    def predict_wins(self, hitters, starters, n_sims=DEFAULT_N_SIMS):
        if len(hitters) < 9:
            raise ValueError("Need 9 hitters (including DH if you use it).")
        if len(starters) != 5:
            raise ValueError("Need exactly 5 starting pitchers.")

        n_sims = int(max(200, min(n_sims, 10000)))

        # 1) Team OPS -> RS/G model
        ops_team = self.roster_to_ops_samples(hitters, n_sims)
        rs_per_g = self.rs_a * ops_team + self.rs_b
        rs_per_g = np.clip(rs_per_g, 2.0, 7.5)

        # 2) Starters RA9 + bullpen blend -> RA/G
        starter_ra9 = self.rotation_to_ra9_samples(starters, n_sims)
        # convert RA9 -> RA/G for starter innings, then add bullpen piece
        ra_per_g = (starter_ra9 * (self.starter_innings / 9.0)) + (self.bullpen_ra9 * (self.bullpen_innings / 9.0))
        ra_per_g = np.clip(ra_per_g, 2.0, 7.5)

        # 3) Wins distribution
        print("RS/G mean:", rs_per_g.mean(), "min/max:", rs_per_g.min(), rs_per_g.max())
        print("RA/G mean:", ra_per_g.mean(), "min/max:", ra_per_g.min(), ra_per_g.max())
        print("starter RA9 mean:", starter_ra9.mean(), "min/max:", starter_ra9.min(), starter_ra9.max())
        print("bullpen RA9:", self.bullpen_ra9)

        wins = _pythag_wins(rs_per_g, ra_per_g)

        def summarize(x):
            return {
                "mean": float(np.mean(x)),
                "p10": float(np.quantile(x, 0.10)),
                "p25": float(np.quantile(x, 0.25)),
                "p50": float(np.quantile(x, 0.50)),
                "p75": float(np.quantile(x, 0.75)),
                "p90": float(np.quantile(x, 0.90)),
            }

        return {
            "games": GAMES,
            "rs_model": {"a": self.rs_a, "b": self.rs_b},
            "assumptions": {"starter_innings": self.starter_innings, "bullpen_innings": self.bullpen_innings},
            "RS_per_G": summarize(rs_per_g),
            "RA_per_G": summarize(ra_per_g),
            "wins": summarize(wins),
        }
