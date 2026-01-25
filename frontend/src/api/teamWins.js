export async function fetchTeamWins({ hitters, starters, n_sims = 1500 }) {
  const res = await fetch("http://localhost:5000/api/team/wins", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ hitters, starters, n_sims }),
  });

  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "Failed to predict team wins");
  return data;
}
