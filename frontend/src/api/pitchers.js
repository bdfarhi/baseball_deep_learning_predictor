export async function fetchPitchers(q) {
  const res = await fetch(
    `http://localhost:5000/api/pitchers/search?q=${encodeURIComponent(q)}`
  );
  if (!res.ok) return [];
  return await res.json(); // [{playerID, fullName}]
}
