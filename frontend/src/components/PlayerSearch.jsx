import React, { useEffect, useRef, useState } from "react";

async function fetchPlayers(q) {
  const res = await fetch(`http://localhost:5000/api/players?q=${encodeURIComponent(q)}`);
  if (!res.ok) return [];
  return await res.json(); // [{playerID, fullName}]
}

export default function PlayerSearch({
  value,
  onChangeValue,
  onPickName,
  placeholder = "Enter player name (e.g., Francisco Lindor)",
}) {
  const [suggestions, setSuggestions] = useState([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const debounceRef = useRef(null);

  const handleChange = (next) => {
    onChangeValue(next);

    const q = next.trim();
    if (q.length < 2) {
      setSuggestions([]);
      setShowSuggestions(false);
      return;
    }

    setShowSuggestions(true);
    if (debounceRef.current) clearTimeout(debounceRef.current);

    debounceRef.current = setTimeout(async () => {
      try {
        const list = await fetchPlayers(q);
        setSuggestions(list);
      } catch {
        setSuggestions([]);
      }
    }, 150);
  };

  const pick = (fullName) => {
    onPickName(fullName);
    setShowSuggestions(false);
    setSuggestions([]);
  };

  const onKeyDown = (e) => {
    if (e.key === "Escape") setShowSuggestions(false);
    if (e.key === "Enter") {
      if (showSuggestions && suggestions.length > 0) {
        pick(suggestions[0].fullName);
      } else {
        onPickName(value.trim());
      }
    }
  };

  useEffect(() => {
    return () => debounceRef.current && clearTimeout(debounceRef.current);
  }, []);

  return (
    <div className="searchInputWrap">
      <input
        className="searchInput"
        value={value}
        placeholder={placeholder}
        onChange={(e) => handleChange(e.target.value)}
        onKeyDown={onKeyDown}
        autoComplete="off"
      />

      {showSuggestions && suggestions.length > 0 && (
        <div className="suggestions">
          {suggestions.map((p) => (
            <button
              key={p.playerID}
              type="button"
              className="suggestionItem"
              onMouseDown={(e) => e.preventDefault()}
              onClick={() => pick(p.fullName)}
            >
              {p.fullName}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
