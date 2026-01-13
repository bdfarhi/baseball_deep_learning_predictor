import React, { useRef, useState } from "react";
import TeamPositionPin from "../components/TeamPositionPin";
import RosterCard from "../components/RosterCard";

const FIELD_POSITIONS = [
  { key: "C",  label: "C",  name: "Catcher" },
  { key: "1B", label: "1B", name: "First Base" },
  { key: "2B", label: "2B", name: "Second Base" },
  { key: "SS", label: "SS", name: "Shortstop" },
  { key: "3B", label: "3B", name: "Third Base" },
  { key: "LF", label: "LF", name: "Left Field" },
  { key: "CF", label: "CF", name: "Center Field" },
  { key: "RF", label: "RF", name: "Right Field" },
  { key: "DH", label: "DH", name: "Designated Hitter" },
];

const ROTATION = [
  { key: "SP1", label: "SP1", name: "Starter 1" },
  { key: "SP2", label: "SP2", name: "Starter 2" },
  { key: "SP3", label: "SP3", name: "Starter 3" },
  { key: "SP4", label: "SP4", name: "Starter 4" },
  { key: "SP5", label: "SP5", name: "Starter 5" },
];

async function fetchPlayers(q) {
  const res = await fetch(`http://localhost:5000/api/players?q=${encodeURIComponent(q)}`);
  if (!res.ok) return [];
  return await res.json();
}

export default function DiamondPage() {
  const [team, setTeam] = useState(() => {
    const init = {};
    for (const p of [...FIELD_POSITIONS, ...ROTATION]) {
      init[p.key] = { text: "", selected: null };
    }
    return init;
  });

  const [activeKey, setActiveKey] = useState(null);
  const [suggestions, setSuggestions] = useState([]);
  const debounceRef = useRef(null);

  const isComplete =
    FIELD_POSITIONS.every((p) => team[p.key]?.selected) &&
    ROTATION.every((p) => team[p.key]?.selected);

  const closeSuggestions = () => {
    setActiveKey(null);
    setSuggestions([]);
  };

  const setText = (key, value) => {
    setTeam((prev) => ({
      ...prev,
      [key]: { ...prev[key], text: value, selected: null },
    }));

    const q = value.trim();
    if (q.length < 2) {
      closeSuggestions();
      return;
    }

    setActiveKey(key);

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

  const activate = (key, value) => {
    const q = (value || "").trim();
    if (q.length >= 2) setActiveKey(key);
  };

  const pick = (key, player) => {
    setTeam((prev) => ({
      ...prev,
      [key]: { text: player.fullName, selected: player },
    }));
    closeSuggestions();
  };

  const clear = (key) => {
    setTeam((prev) => ({
      ...prev,
      [key]: { text: "", selected: null },
    }));
    if (activeKey === key) closeSuggestions();
  };

  const lineupSections = [
    { title: "Lineup + Defense", positions: FIELD_POSITIONS },
    { title: "Starting Rotation", positions: ROTATION },
  ];

  return (
    <div className="diamondTab">
      <div className="diamondHeader">
        <div>
          <h2 className="diamondTitle">Build a Team</h2>
          <p className="diamondSubtitle">
            Fill defense + DH on the field, and pick 5 starters in the rotation.
          </p>
        </div>

        <div className="diamondActions">
          <button className="btn btnSecondary" disabled>
            Estimate Wins (coming soon)
          </button>
          <div className={`teamStatus ${isComplete ? "teamStatus--ready" : ""}`}>
            {isComplete ? "Team complete ✅" : "Fill all positions"}
          </div>
        </div>
      </div>

      <div className="diamondWrap">
        {/* FIELD */}
        <div className="field">
          <div className="infield" />
          <div className="base base--home" title="Home" />
          <div className="base base--first" title="1st Base" />
          <div className="base base--second" title="2nd Base" />
          <div className="base base--third" title="3rd Base" />

          {/* Diamond pins (NO pitcher pin anymore) */}
          <TeamPositionPin posKey="C"  label="C"  title="Catcher" className="pin--c"
            value={team.C.text} selected={team.C.selected}
            isActive={activeKey === "C"} suggestions={activeKey === "C" ? suggestions : []}
            onChangeText={setText} onPick={pick} onClear={clear}
            onCloseSuggestions={closeSuggestions} onActivate={activate}
          />

          <TeamPositionPin posKey="1B" label="1B" title="First Base" className="pin--1b"
            value={team["1B"].text} selected={team["1B"].selected}
            isActive={activeKey === "1B"} suggestions={activeKey === "1B" ? suggestions : []}
            onChangeText={setText} onPick={pick} onClear={clear}
            onCloseSuggestions={closeSuggestions} onActivate={activate}
          />

          <TeamPositionPin posKey="2B" label="2B" title="Second Base" className="pin--2b"
            value={team["2B"].text} selected={team["2B"].selected}
            isActive={activeKey === "2B"} suggestions={activeKey === "2B" ? suggestions : []}
            onChangeText={setText} onPick={pick} onClear={clear}
            onCloseSuggestions={closeSuggestions} onActivate={activate}
          />

          <TeamPositionPin posKey="SS" label="SS" title="Shortstop" className="pin--ss"
            value={team.SS.text} selected={team.SS.selected}
            isActive={activeKey === "SS"} suggestions={activeKey === "SS" ? suggestions : []}
            onChangeText={setText} onPick={pick} onClear={clear}
            onCloseSuggestions={closeSuggestions} onActivate={activate}
          />

          <TeamPositionPin posKey="3B" label="3B" title="Third Base" className="pin--3b"
            value={team["3B"].text} selected={team["3B"].selected}
            isActive={activeKey === "3B"} suggestions={activeKey === "3B" ? suggestions : []}
            onChangeText={setText} onPick={pick} onClear={clear}
            onCloseSuggestions={closeSuggestions} onActivate={activate}
          />

          <TeamPositionPin posKey="LF" label="LF" title="Left Field" className="pin--lf"
            value={team.LF.text} selected={team.LF.selected}
            isActive={activeKey === "LF"} suggestions={activeKey === "LF" ? suggestions : []}
            onChangeText={setText} onPick={pick} onClear={clear}
            onCloseSuggestions={closeSuggestions} onActivate={activate}
          />

          <TeamPositionPin posKey="CF" label="CF" title="Center Field" className="pin--cf"
            value={team.CF.text} selected={team.CF.selected}
            isActive={activeKey === "CF"} suggestions={activeKey === "CF" ? suggestions : []}
            onChangeText={setText} onPick={pick} onClear={clear}
            onCloseSuggestions={closeSuggestions} onActivate={activate}
          />

          <TeamPositionPin posKey="RF" label="RF" title="Right Field" className="pin--rf"
            value={team.RF.text} selected={team.RF.selected}
            isActive={activeKey === "RF"} suggestions={activeKey === "RF" ? suggestions : []}
            onChangeText={setText} onPick={pick} onClear={clear}
            onCloseSuggestions={closeSuggestions} onActivate={activate}
          />

          {/* NEW: DH pin */}
          <TeamPositionPin posKey="DH" label="DH" title="Designated Hitter" className="pin--dh"
            value={team.DH.text} selected={team.DH.selected}
            isActive={activeKey === "DH"} suggestions={activeKey === "DH" ? suggestions : []}
            onChangeText={setText} onPick={pick} onClear={clear}
            onCloseSuggestions={closeSuggestions} onActivate={activate}
          />
        </div>

        {/* SIDEBAR */}
        <div className="sideStack">
          <div className="rotationCard card">
            <div className="rotationTitleRow">
              <h3 className="rotationTitle">Starting Rotation</h3>
              <span className="rotationHint">Pick 5 starters</span>
            </div>

            <div className="rotationGrid">
              {ROTATION.map((sp) => (
                <TeamPositionPin
                  key={sp.key}
                  mode="inline"
                  posKey={sp.key}
                  label={sp.label}
                  title={sp.name}
                  value={team[sp.key].text}
                  selected={team[sp.key].selected}
                  isActive={activeKey === sp.key}
                  suggestions={activeKey === sp.key ? suggestions : []}
                  onChangeText={setText}
                  onPick={pick}
                  onClear={clear}
                  onCloseSuggestions={closeSuggestions}
                  onActivate={activate}
                />
              ))}
            </div>
          </div>

          <RosterCard sections={lineupSections} team={team} />
        </div>
      </div>
    </div>
  );
}
