from torch import pi
from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import pickle
import os
from predictor import BaseballPredictor
from data_processing import (
    compute_season_obp_slg, 
    get_age_of_players,
    ZScaler
)

app = Flask(__name__)
CORS(app)

# Global predictor instance
predictor = None

players_index = None
MIN_PA_FULLTIME = 100

def initialize_predictor():
    global predictor, players_index

    print("Loading data...")
    batting = pd.read_csv('../data/Batting.csv')
    people = pd.read_csv('../data/People.csv')

    # Build player search index (MLB only-ish via People.csv; you can filter further if you want)
    pi = people[['playerID', 'nameFirst', 'nameLast']].dropna().copy()
    pi['fullName'] = (pi['nameFirst'].str.strip() + ' ' + pi['nameLast'].str.strip())
    pi['fullNameLower'] = pi['fullName'].str.lower()
    players_index = pi[['playerID', 'fullName', 'fullNameLower']]

    print("Processing season stats...")
    season_stats = compute_season_obp_slg(batting)
    season_stats = get_age_of_players(season_stats, people)
    # Take each player's most recent season row and keep only those with enough PA
    last_season = (
    season_stats.sort_values(["playerID", "yearID"])
    .groupby("playerID", as_index=False)
    .tail(1)
    )

    eligible_ids = set(
    last_season[last_season["PA"] >= MIN_PA_FULLTIME]["playerID"].astype(str)
    )

# Build searchable player index from People.csv, but keep only eligible
    pi = people[['playerID', 'nameFirst', 'nameLast']].dropna().copy()
    pi["playerID"] = pi["playerID"].astype(str)
    pi = pi[pi["playerID"].isin(eligible_ids)].copy()

    pi["fullName"] = (pi["nameFirst"].str.strip() + " " + pi["nameLast"].str.strip())
    pi["fullNameLower"] = pi["fullName"].str.lower()
    players_index = pi[["playerID", "fullName", "fullNameLower"]]

    print(f"Autocomplete eligible players (PA >= {MIN_PA_FULLTIME}): {len(players_index)}")
    print("Loading scalers...")
    with open('../models/cond_scaler.pkl', 'rb') as f:
        cond_scaler = pickle.load(f)
    with open('../models/y_scaler.pkl', 'rb') as f:
        y_scaler = pickle.load(f)

    print("Initializing predictor...")
    predictor = BaseballPredictor(
        model_path='../models/best_model.pt',
        cond_scaler=cond_scaler,
        y_scaler=y_scaler,
        season_stats=season_stats,
        people=people
    )
    print("Predictor ready!")


@app.route('/api/players', methods=['GET'])
def players():
    q = (request.args.get('q') or '').strip().lower()
    if not q or players_index is None:
        return jsonify([])

    # simple contains match; fast enough for small lists
    matches = players_index[players_index['fullNameLower'].str.contains(q, na=False)]

    # limit results
    out = matches.head(12)[['playerID', 'fullName']].to_dict(orient='records')
    return jsonify(out)


@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"})

@app.route('/api/predict', methods=['POST'])
def predict():
    try:
        data = request.json
        player_name = data.get('name')
        
        if not player_name:
            return jsonify({'error': 'Player name is required'}), 400
        
        result = predictor.predict(player_name)
        return jsonify(result)
    
    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        return jsonify({'error': f'Prediction failed: {str(e)}'}), 500

if __name__ == '__main__':
    initialize_predictor()
    app.run(host='0.0.0.0', port=5000, debug=True)