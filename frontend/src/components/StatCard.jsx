import React from "react";

export default function StatCard({ title, stats, icon: Icon, variant = "blue" }) {
  if (!stats) return null;

  return (
    <div className={`card statCard statCard--${variant}`}>
      <div className="statCardHeader">
        <h3 className="statCardTitle">{title}</h3>
        <Icon className="statCardIcon" size={24} />
      </div>

      <div className="statCardBody">
        <div className="statRow">
          <span className="muted">Mean:</span>
          <span className="statMean">{stats.mean.toFixed(3)}</span>
        </div>

        <div className="statDivider" />

        <div className="statGrid">
          <div className="statRow small">
            <span className="muted">P10 (downside):</span>
            <span className="statVal danger">{stats.p10.toFixed(3)}</span>
          </div>
          <div className="statRow small">
            <span className="muted">P25:</span>
            <span className="statVal">{stats.p25.toFixed(3)}</span>
          </div>
          <div className="statRow small">
            <span className="muted">P50 (median):</span>
            <span className="statVal primary">{stats.p50.toFixed(3)}</span>
          </div>
          <div className="statRow small">
            <span className="muted">P75:</span>
            <span className="statVal">{stats.p75.toFixed(3)}</span>
          </div>
          <div className="statRow small">
            <span className="muted">P90 (upside):</span>
            <span className="statVal success">{stats.p90.toFixed(3)}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
