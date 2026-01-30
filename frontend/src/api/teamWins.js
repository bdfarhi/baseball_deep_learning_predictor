const API_BASE = process.env.REACT_APP_API_URL || "http://localhost:5000";

export async function fetchTeamWins({ hitters, starters, n_sims = 1500 }) {
  const res = await fetch(`${API_BASE}/api/team/wins`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ hitters, starters, n_sims }),
  });

  // handle non-JSON error responses safely
  let data;
  try {
    data = await res.json();
  } catch {
    data = null;
  }

  if (!res.ok) {
    const msg =
      (data && data.error) || `Failed to predict team wins (HTTP ${res.status})`;
    throw new Error(msg);
  }

  return data;
}
