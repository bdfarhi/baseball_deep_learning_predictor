import React from "react";

export default function Tabs({ activeTab, onChange, tabs }) {
  return (
    <div className="tabs">
      {tabs.map((t) => (
        <button
          key={t.key}
          type="button"
          className={`tabBtn ${activeTab === t.key ? "tabBtn--active" : ""}`}
          onClick={() => onChange(t.key)}
        >
          {t.label}
        </button>
      ))}
    </div>
  );
}
