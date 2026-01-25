import React from "react";
import { Trophy, AlertCircle } from "lucide-react";

export default function WinsCard({ result, loading, error }) {
  // Loading state
  if (loading) {
    return (
      <div className="card">
        <div className="cardTitle" style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <Trophy size={18} />
          Estimated Wins
        </div>
        <div className="muted" style={{ marginTop: 8 }}>
          Estimating…
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="card errorBox" style={{ display: "flex", gap: 10, alignItems: "center" }}>
        <AlertCircle size={20} />
        <span>{error}</span>
      </div>
    );
  }

  // Empty state (before user presses button)
  if (!result) {
    return (
      <div className="card">
        <div className="cardTitle" style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <Trophy size={18} />
          Estimated Wins
        </div>
        <div className="muted" style={{ marginTop: 8 }}>
          Build a full team, then press “Estimate Wins”.
        </div>
      </div>
    );
  }

  // Your API shape: result.wins is an object { mean, p10, p25, p75, p90, ... }
  const w = result.wins;
  const fmt = (x) => (Number.isFinite(x) ? x.toFixed(1) : "—");

  return (
    <div className="card">
      <div className="cardTitle" style={{ display: "flex", gap: 8, alignItems: "center" }}>
        <Trophy size={18} />
        Estimated Wins
      </div>

      <div style={{ fontSize: 42, fontWeight: 800, marginTop: 8 }}>
        {fmt(w?.mean)}
      </div>

      {w && (
        <div style={{ marginTop: 12, opacity: 0.9 }}>
          <div className="muted" style={{ marginBottom: 6 }}>
            Percentiles
          </div>

          <div style={{ display: "flex", gap: 14, flexWrap: "wrap" }}>
            <span>P10: {fmt(w.p10)}</span>
            <span>P25: {fmt(w.p25)}</span>
            <span>P75: {fmt(w.p75)}</span>
            <span>P90: {fmt(w.p90)}</span>
          </div>
        </div>
      )}
    </div>
  );
}
