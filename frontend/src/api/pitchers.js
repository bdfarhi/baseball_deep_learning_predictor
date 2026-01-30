const API_BASE = process.env.REACT_APP_API_URL || "http://localhost:5000";
export async function fetchPitchers(q) {
  const url = new URL(`${API_BASE}/api/pitchers/search`);
  url.searchParams.set("q", q || "");

  const res = await fetch(url.toString());
  if (!res.ok) return [];
  return await res.json(); // [{ playerID, fullName }]
}