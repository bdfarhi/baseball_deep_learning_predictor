import React from "react";

export default function WinsInline({ result, loading, error }) {
  if (loading) {
    return <div className="winsInline muted">Estimating…</div>;
  }

  if (error) {
    return <div className="winsInline error">{error}</div>;
  }

  if (!result?.wins?.mean) {
    return <div className="winsInline muted">—</div>;
  }

  return (
    <div className="winsInline">
      <span className="winsValue">{result.wins.mean.toFixed(1)}</span>
      <span className="winsLabel">Wins</span>
    </div>
  );
}
