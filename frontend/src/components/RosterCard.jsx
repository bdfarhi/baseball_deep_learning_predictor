import React from "react";

export default function RosterCard({ sections, team }) {
  return (
    <div className="rosterCard card">
      <h3 className="rosterTitle">Roster</h3>

      <div className="rosterList">
        {sections.map((sec) => (
          <div key={sec.title} className="rosterSection">
            <div className="rosterSectionTitle">{sec.title}</div>

            <div className="rosterSectionGrid">
              {sec.positions.map((p) => (
                <div key={p.key} className="rosterRow">
                  <div className="rosterPos">{p.label}</div>
                  <div className="rosterName">
                    {team[p.key]?.selected ? (
                      team[p.key].selected.fullName
                    ) : (
                      <span className="muted">— empty —</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      <div className="rosterHint">
        Later: you’ll call your wins model using each selected player’s projection distributions.
      </div>
    </div>
  );
}
