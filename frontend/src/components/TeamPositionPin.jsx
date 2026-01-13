import React from "react";

export default function TeamPositionPin({
  posKey,
  label,
  title,
  className = "",
  mode = "pin", // "pin" | "inline"
  value,
  selected,
  isActive,
  suggestions,
  onChangeText,
  onPick,
  onClear,
  onCloseSuggestions,
  onActivate,
}) {
  const rootClass =
    mode === "inline"
      ? `posPin posPin--inline ${className}`
      : `posPin ${className}`;

  return (
    <div className={rootClass}>
      <div className="posPinTop">
        <div className="posBadge" title={title}>{label}</div>
        <div className="posTitle">{title}</div>
      </div>

      <div className="posInputWrap">
        <input
          className={`posInput ${selected ? "posInput--selected" : ""}`}
          value={value}
          placeholder="Select player..."
          onChange={(e) => onChangeText(posKey, e.target.value)}
          onFocus={() => onActivate(posKey, value)}
          onKeyDown={(e) => {
            if (e.key === "Escape") onCloseSuggestions();
            if (e.key === "Enter" && isActive && suggestions.length > 0) {
              onPick(posKey, suggestions[0]);
            }
          }}
          autoComplete="off"
        />

        {value && (
          <button
            className="posClearBtn"
            type="button"
            onMouseDown={(e) => e.preventDefault()}
            onClick={() => onClear(posKey)}
          >
            ×
          </button>
        )}

        {isActive && suggestions.length > 0 && (
          <div className="posSuggestions">
            {suggestions.map((p) => (
              <button
                key={p.playerID}
                type="button"
                className="posSuggestionItem"
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => onPick(posKey, p)}
              >
                {p.fullName}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

