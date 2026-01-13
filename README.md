# Baseball Predictor (Full-Stack) — 2026 Projections

A full-stack web app for MLB player projections and roster building.

- **Frontend:** React UI with two tabs:
  - **Predictions**: single-player projection lookup.
  - **Build a Team**: interactive baseball **diamond** (defense + DH) plus **5-starter rotation** selection and a roster summary panel.
- **Backend:** Flask API serving projections.
  - **Hitters ’26 projections**: Tabular diffusion (DDPM-style) generating distribution summaries for **OBP / SLG / OPS**.
  - **Pitchers ’26 projections (optional feature)**: Quantile Gradient Boosting models producing quantiles for **RA9** and **FIP (no constant)**.

> Roadmap: “Wins prediction” model that converts a selected roster’s projected distributions into estimated team wins.

---

## Table of Contents
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Data](#data)
- [Quickstart](#quickstart)
  - [Backend](#backend)
  - [Frontend](#frontend)
  - [Run Both Together](#run-both-together)
- [Model Artifacts](#model-artifacts)
  - [Hitter DDPM](#hitter-ddpm)
  - [Pitcher Quantile GBM (Optional)](#pitcher-quantile-gbm-optional)
- [API Documentation](#api-documentation)
  - [Health](#health)
  - [Hitter Projection](#hitter-projection)
  - [Player Search (Autocomplete)](#player-search-autocomplete)
  - [Pitcher Projection (Optional)](#pitcher-projection-optional)
  - [Pitcher Search (Optional)](#pitcher-search-optional)
- [Troubleshooting](#troubleshooting)
- [Roadmap](#roadmap)

---

## Architecture

React (frontend) calls Flask (backend) over HTTP:
- Frontend: `http://localhost:3000`
- Backend: `http://localhost:5000`

Backend loads:
- Lahman CSVs from `./data`
- Pretrained model artifacts from `./models`

---

## Tech Stack

- **Frontend:** React, CSS (App.css)
- **Backend:** Flask, flask-cors
- **ML:** PyTorch (hitter DDPM), scikit-learn (pitcher quantile GBM)
- **Data:** pandas, numpy
- **Dataset:** Lahman Baseball Database CSV exports

---

## Project Structure

baseball-predictor/
├─ backend/
│ ├─ app.py
│ ├─ data_processing.py
│ ├─ model.py
│ ├─ predictor.py
│ ├─ save_scalars.py
│ ├─ train_model.py
│ ├─ requirements.txt
│ ├─ pitch_processing.py # optional pitcher feature
│ ├─ train_pitch_quantiles.py # optional pitcher feature
│ └─ pitcher_gbm_predictor.py # optional pitcher feature
├─ frontend/
│ ├─ src/
│ │ ├─ App.js
│ │ ├─ App.css
│ │ ├─ pages/ # recommended organization
│ │ └─ components/ # recommended organization
│ └─ package.json
├─ data/
│ ├─ Batting.csv
│ ├─ People.csv
│ └─ Pitching.csv
└─ models/
├─ best_model.pt
├─ cond_scaler.pkl
├─ y_scaler.pkl
└─ pitch_gbm__q.joblib 

---

## Data

This project expects Lahman CSVs in `./data/`:
- `Batting.csv`
- `Pitching.csv`
- `People.csv`

The backend aggregates by `(playerID, yearID)` and derives:
- Hitters: PA, OBP, SLG (+ age from `People.csv`)
- Pitchers: IP, RA9, K9, BB9, HR9, FIP(no constant) (+ age)

---

## Quickstart

### Backend

#### 1) Recommended Python Version
For easiest installs (especially with PyTorch + numpy wheels), use **Python 3.10 or 3.11**.

> If you’re on Python 3.13, some pinned versions (like numpy 1.24.x) may not have wheels and will try to build from source.

#### 2) Create venv
From repo root:
```bash
cd backend
python -m venv .venv

Activate:

Windows PowerShell:

.\.venv\Scripts\Activate.ps1


macOS/Linux:

source .venv/bin/activate

3) Install deps
python -m pip install -U pip setuptools wheel
pip install -r requirements.txt

4) Run the server
python app.py


Backend should be running at:

http://localhost:5000

Frontend

From repo root:

cd frontend
npm install
npm start


Frontend should be running at:

http://localhost:3000

Run Both Together

Option A (simple): use two terminals:

Terminal 1:

cd backend
.\.venv\Scripts\Activate.ps1   # Windows
python app.py


Terminal 2:

cd frontend
npm start


Option B (optional): use concurrently from the repo root (requires adding a root package.json).

Model Artifacts
Hitter DDPM

The hitter predictor (backend/predictor.py) loads:

models/best_model.pt — trained DDPM model checkpoint

models/cond_scaler.pkl — scaler for conditional features

models/y_scaler.pkl — scaler for model outputs (deltas)

It simulates many seasons per player and returns distribution summaries:

mean, p10, p25, p50, p75, p90 for OBP / SLG / OPS

Pitcher Quantile GBM (Optional)

If you enable the pitcher feature, it trains and saves quantile models:

pitch_gbm_logRA9_next_q10.joblib, q50, q90

pitch_gbm_FIP_next_q10.joblib, q50, q90

These produce P10/P50/P90 and interpolate P25/P75 for UI display.

API Documentation

Base URL (local): http://localhost:5000

Health

GET /api/health

Response:

{ "status": "ok" }

Hitter Projection

POST /api/predict

Request body:

{ "name": "Francisco Lindor" }


Response (shape):

{
  "name": "Francisco Lindor",
  "playerID": "lindofr01",
  "upcoming_year": 2026,
  "condition_used": {
    "prev_year": 2025,
    "prev_OBP": 0.337,
    "prev_SLG": 0.461,
    "prev_PA": 670,
    "age_next": 32.0
  },
  "OBP": { "mean": 0.334, "p10": 0.305, "p25": 0.320, "p50": 0.335, "p75": 0.349, "p90": 0.365 },
  "SLG": { "mean": 0.468, "p10": 0.410, "p25": 0.440, "p50": 0.468, "p75": 0.495, "p90": 0.525 },
  "OPS": { "mean": 0.802, "p10": 0.720, "p25": 0.760, "p50": 0.803, "p75": 0.842, "p90": 0.885 }
}


Errors:

400 if name missing

404 if player not found / no history

500 for unexpected failures

Player Search (Autocomplete)

This endpoint is used by the UI to suggest player names while typing.
If you haven’t implemented it yet, add it so the frontend doesn’t require exact spelling.

GET /api/players/search?q=<query>

Example:

/api/players/search?q=lin

Response:

{ "results": ["Francisco Lindor", "Bo Bichette", "..."] }


Eligibility filter (recommended):
Only include “full-time” hitters using a single threshold such as:

MIN_PA_FULLTIME from the most recent season

Pitcher Projection (Optional)

POST /api/pitcher/predict

Request body:

{ "name": "Gerrit Cole" }


Response (shape):

{
  "name": "Gerrit Cole",
  "playerID": "colege01",
  "upcoming_year": 2026,
  "condition_used": {
    "prev_year": 2025,
    "prev_IP": 165.2,
    "prev_RA9": 3.85,
    "prev_FIP_no_const": 1.42,
    "age_next": 35.0
  },
  "RA9": { "mean": 4.01, "p10": 3.20, "p25": 3.55, "p50": 4.00, "p75": 4.40, "p90": 4.95 },
  "FIP_no_const": { "mean": 1.50, "p10": 0.70, "p25": 1.05, "p50": 1.50, "p75": 1.95, "p90": 2.60 }
}

Pitcher Search (Optional)

GET /api/pitchers/search?q=<query>

Response:

{ "results": ["Gerrit Cole", "Max Fried", "..."] }


Eligibility filter (recommended):
Only include “full-time starters” from the most recent season using one threshold:

MIN_IP_STARTER (example: 120)

Troubleshooting
1) BackendUnavailable: Cannot import 'setuptools.build_meta'

Fix:

python -m pip install -U pip setuptools wheel
pip install -r requirements.txt

2) numpy builds from source / install fails

This often happens when your Python version doesn’t have wheels for the pinned numpy version.

Recommended fix:

Use Python 3.10 or 3.11, recreate venv, reinstall.

3) PyTorch install mismatch

Torch wheels vary by Python version. For simplest setup:

Use Python 3.10/3.11 and the torch==2.1.0 pin (as configured)

4) Frontend styling not showing

If you previously used Tailwind classnames, ensure App.css is imported:

import "./App.css";

Roadmap

Add pitcher projections (if not already integrated).

Create a “Wins Model”:

Aggregate the roster’s projected distributions into team-level runs scored/allowed.

Estimate wins (e.g., Pythagorean expectation or a trained wins regressor).

Add bullpen modeling / innings allocation.

Persist “saved rosters” and export/share links.


