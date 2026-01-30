from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import pickle

from predictor import BaseballPredictor
from data_processing import compute_season_obp_slg, get_age_of_players
from pitcher_gbm_predictor import PitcherGBMPredictor
from pitch_processing import compute_season_pitching, add_age
from team_wins_predictor import TeamWinsPredictor
from threading import Lock, Thread
from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / ".." / "data"
MODELS_DIR = BASE_DIR / ".." / "models"




app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": os.getenv("FRONTEND_ORIGIN", "*")}})
_init_lock = Lock()
_initialized = False

def _init_async():
    global _initialized
    with _init_lock:
        if not _initialized:
            initialize_predictor()
            _initialized = True

@app.before_request
def ensure_init():
    global _initialized
    if not _initialized:
        Thread(target=_init_async, daemon=True).start()

# -------- Globals used by routes --------
predictor = None
pitcher_predictor = None
pitchers_index = None


players_index = None
team_wins_predictor = None
eligible_pitchers = []

MIN_PA_FULLTIME = 100
MIN_IP_STARTER = 50
UPCOMING_YEAR = 2026
LAST_YEAR = UPCOMING_YEAR - 1

def initialize_predictor():
    global predictor, players_index, pitcher_predictor, eligible_pitchers, pitchers_index, team_wins_predictor

    print("Loading data...")
    batting = pd.read_csv(DATA_DIR / "Batting.csv")
    people = pd.read_csv(DATA_DIR / "People.csv")
    pitching = pd.read_csv(DATA_DIR / "Pitching.csv")
    teams = pd.read_csv(DATA_DIR / "Teams.csv")

    # ---------- Pitchers: build eligible list + predictor ----------
    pitch_season = compute_season_pitching(pitching)
    pitch_season = add_age(pitch_season, people)

    last = pitch_season[pitch_season["yearID"] == LAST_YEAR].copy()
    last = last[last["IP"] >= MIN_IP_STARTER]
    eligible_pitcher_ids = set(last["playerID"].astype(str).unique().tolist())

    pi_p = people[["playerID", "nameFirst", "nameLast"]].dropna().copy()
    pi_p["playerID"] = pi_p["playerID"].astype(str)
    pi_p = pi_p[pi_p["playerID"].isin(eligible_pitcher_ids)].copy()
    pi_p["fullName"] = pi_p["nameFirst"].str.strip() + " " + pi_p["nameLast"].str.strip()
    pi_p["fullNameLower"] = pi_p["fullName"].str.lower()
    pitchers_index = pi_p[["playerID", "fullName", "fullNameLower"]]
    print(f"Autocomplete eligible pitchers (IP >= {MIN_IP_STARTER}): {len(pitchers_index)}")

    eligible_pitchers = sorted(pi_p["fullName"].unique().tolist())

    pitcher_predictor = PitcherGBMPredictor(
        people_df=people,
        season_pitching_df=pitch_season,
        models_dir=str(MODELS_DIR)
    )

    # ---------- Hitters: season stats + eligible autocomplete list ----------
    print("Processing season stats...")
    season_stats = compute_season_obp_slg(batting)
    season_stats = get_age_of_players(season_stats, people)

    last_season = (
        season_stats.sort_values(["playerID", "yearID"])
        .groupby("playerID", as_index=False)
        .tail(1)
    )

    eligible_ids = set(
        last_season[last_season["PA"] >= MIN_PA_FULLTIME]["playerID"].astype(str).tolist()
    )

    pi_df = people[["playerID", "nameFirst", "nameLast"]].dropna().copy()
    pi_df["playerID"] = pi_df["playerID"].astype(str)
    pi_df = pi_df[pi_df["playerID"].isin(eligible_ids)].copy()
    pi_df["fullName"] = pi_df["nameFirst"].str.strip() + " " + pi_df["nameLast"].str.strip()
    pi_df["fullNameLower"] = pi_df["fullName"].str.lower()
    players_index = pi_df[["playerID", "fullName", "fullNameLower"]]
    print(f"Autocomplete eligible hitters (PA >= {MIN_PA_FULLTIME}): {len(players_index)}")

    # ---------- Hitter predictor ----------
    print("Loading scalers...")
    with open(MODELS_DIR / "cond_scaler.pkl", "rb") as f:
        cond_scaler = pickle.load(f)
    with open(MODELS_DIR / "y_scaler.pkl", "rb") as f:
        y_scaler = pickle.load(f)


    print("Initializing hitter predictor...")
    predictor = BaseballPredictor(
        model_path=str(MODELS_DIR / "best_model.pt"),
        cond_scaler=cond_scaler,
        y_scaler=y_scaler,
        season_stats=season_stats,
        people=people
    )

    # ---------- Team wins predictor (NOW predictor exists) ----------
    # teams = pd.read_csv("../data/Teams.csv")

    team_wins_predictor = TeamWinsPredictor(
        hitter_predictor=predictor,
        pitcher_predictor=pitcher_predictor,
        batting_df=batting,
        teams_df=teams,
    )

    print("Predictors ready!")

# ------------------ Routes ------------------

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/api/players", methods=["GET"])
def players():
    q = (request.args.get("q") or "").strip().lower()
    if not q or players_index is None:
        return jsonify([])

    matches = players_index[players_index["fullNameLower"].str.contains(q, na=False)]
    out = matches.head(12)[["playerID", "fullName"]].to_dict(orient="records")
    return jsonify(out)

@app.route("/api/pitchers/search", methods=["GET"])
def pitchers_search():
    q = (request.args.get("q") or "").strip().lower()
    if not q or pitchers_index is None:
        return jsonify([])

    matches = pitchers_index[pitchers_index["fullNameLower"].str.contains(q, na=False)]
    out = matches.head(12)[["playerID", "fullName"]].to_dict(orient="records")
    return jsonify(out)



@app.route("/api/predict", methods=["POST"])
def predict_hitter():
    try:
        data = request.json or {}
        player_name = data.get("name")
        if not player_name:
            return jsonify({"error": "Player name is required"}), 400
        return jsonify(predictor.predict(player_name))
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": f"Prediction failed: {str(e)}"}), 500


@app.route("/api/pitcher/predict", methods=["POST"])
def predict_pitcher():
    try:
        data = request.json or {}
        name = data.get("name")
        if not name:
            return jsonify({"error": "Pitcher name is required"}), 400
        return jsonify(pitcher_predictor.predict(name))
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": f"Pitch prediction failed: {str(e)}"}), 500

@app.route("/api/team/wins", methods=["POST"])
def team_wins():
    try:
        data = request.get_json(force=True) or {}
        hitters = data.get("hitters", [])
        starters = data.get("starters", [])
        n_sims = int(data.get("n_sims", 1500))

        if len(hitters) != 9:
            return jsonify({"error": f"Expected 9 hitters, got {len(hitters)}"}), 400
        if len(starters) != 5:
            return jsonify({"error": f"Expected 5 starters, got {len(starters)}"}), 400

        if team_wins_predictor is None:
            return jsonify({"error": "Team wins predictor not initialized"}), 500

        result = team_wins_predictor.predict_wins(hitters, starters, n_sims=n_sims)
        return jsonify(result)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Team wins failed: {str(e)}"}), 500

if __name__ == "__main__":
    initialize_predictor()
    app.run(host="0.0.0.0", port=5000, debug=True)
