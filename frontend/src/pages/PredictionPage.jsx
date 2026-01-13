import React, { useState } from "react";
import { Search, TrendingUp, Award, AlertCircle } from "lucide-react";

import PlayerSearch from "../components/PlayerSearch";
import StatCard from "../components/StatCard";

async function getPrediction(name) {
  const res = await fetch("http://localhost:5000/api/predict", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });

  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.error || "Failed to get prediction");
  }

  return await res.json();
}

export default function PredictionsPage() {
  const [playerName, setPlayerName] = useState("");
  const [loading, setLoading] = useState(false);
  const [prediction, setPrediction] = useState(null);
  const [error, setError] = useState("");

  const submit = async (nameFromEnter) => {
    const name = (nameFromEnter ?? playerName).trim();
    if (!name) {
      setError("Please enter a player name");
      return;
    }

    setLoading(true);
    setError("");
    setPrediction(null);

    try {
      const result = await getPrediction(name);
      setPrediction(result);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <div className="card searchCard">
        <div className="searchRow">
          <PlayerSearch
            value={playerName}
            onChangeValue={(v) => {
              setPlayerName(v);
              setError("");
              setPrediction(null);
            }}
            onPickName={(picked) => {
              // If Enter triggers this with current value, picked may equal current text
              setPlayerName(picked);
              submit(picked);
            }}
          />

          <button className="btn" onClick={() => submit()} disabled={loading}>
            {loading ? (
              <>
                <span className="spinner" />
                Analyzing...
              </>
            ) : (
              <>
                <Search size={20} />
                Predict
              </>
            )}
          </button>
        </div>

        {error && (
          <div className="errorBox">
            <AlertCircle size={20} />
            <span>{error}</span>
          </div>
        )}
      </div>

      {prediction && (
        <div className="results">
          <div className="card resultHeader">
            <h2 className="resultTitle">
              {prediction.name} — {prediction.upcoming_year} Projection
            </h2>

            <div className="prevBox">
              <h3 className="prevTitle">Previous Season Stats:</h3>
              <div className="prevGrid">
                <div className="prevItem">
                  <span className="muted">OBP:</span>
                  <span className="bold">{prediction.condition_used.prev_OBP.toFixed(3)}</span>
                </div>
                <div className="prevItem">
                  <span className="muted">SLG:</span>
                  <span className="bold">{prediction.condition_used.prev_SLG.toFixed(3)}</span>
                </div>
                <div className="prevItem">
                  <span className="muted">PA:</span>
                  <span className="bold">{prediction.condition_used.prev_PA}</span>
                </div>
                <div className="prevItem">
                  <span className="muted">Age:</span>
                  <span className="bold">{prediction.condition_used.age_next}</span>
                </div>
              </div>
            </div>
          </div>

          <div className="statsGrid">
            <StatCard title="On-Base Percentage (OBP)" stats={prediction.OBP} icon={TrendingUp} variant="blue" />
            <StatCard title="Slugging Percentage (SLG)" stats={prediction.SLG} icon={Award} variant="purple" />
            <StatCard title="OPS (OBP + SLG)" stats={prediction.OPS} icon={TrendingUp} variant="green" />
          </div>

          <div className="callout">
            <h3 className="calloutTitle">Interpretation:</h3>
            <p className="calloutText">50% of simulated seasons fall between:</p>
            <ul className="calloutList">
              <li>• OBP: {prediction.OBP.p25.toFixed(3)} — {prediction.OBP.p75.toFixed(3)}</li>
              <li>• SLG: {prediction.SLG.p25.toFixed(3)} — {prediction.SLG.p75.toFixed(3)}</li>
              <li>• OPS: {prediction.OPS.p25.toFixed(3)} — {prediction.OPS.p75.toFixed(3)}</li>
            </ul>
          </div>
        </div>
      )}
    </>
  );
}
