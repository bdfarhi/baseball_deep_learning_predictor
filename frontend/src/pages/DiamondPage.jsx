import React, { useEffect, useRef, useState } from "react";
import TeamPositionPin from "../components/TeamPositionPin";
import RosterCard from "../components/RosterCard";
import WinsCard from "../components/WinsCard";
import TeamWins from "../components/WinsCard";
import WinsInline from "../components/WinsInline";


import { fetchTeamWins } from "../api/teamWins";
import { fetchPitchers } from "../api/pitchers";

const HITTER_KEYS = ["C", "1B", "2B", "SS", "3B", "LF", "CF", "RF", "DH"];
const STARTER_KEYS = ["SP1", "SP2", "SP3", "SP4", "SP5"];

function buildHitters(team) {
  return HITTER_KEYS.map((k) => team[k]?.selected?.fullName).filter(Boolean);
}

function buildStarters(team) {
  return STARTER_KEYS.map((k) => team[k]?.selected?.fullName).filter(Boolean);
}

const FIELD_POSITIONS = [
  { key: "C", label: "C", name: "Catcher" },
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
  const res = await fetch(
    `http://localhost:5000/api/players?q=${encodeURIComponent(q)}`
  );
  if (!res.ok) return [];
  return await res.json(); // [{playerID, fullName}]
}

export default function DiamondPage() {
  const isPitcherSlot = (key) => key.startsWith("SP");

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

  const [winsLoading, setWinsLoading] = useState(false);
  const [winsError, setWinsError] = useState("");
  const [winsResult, setWinsResult] = useState(null);

  useEffect(() => {
    return () => debounceRef.current && clearTimeout(debounceRef.current);
  }, []);

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

    setWinsResult(null);
    setWinsError("");

    const q = value.trim();
    if (q.length < 2) {
      if (activeKey === key) closeSuggestions();
      return;
    }

    setActiveKey(key);

    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(async () => {
      try {
        const list = isPitcherSlot(key) ? await fetchPitchers(q) : await fetchPlayers(q);
        setSuggestions(Array.isArray(list) ? list : []);
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
    setWinsResult(null);
    setWinsError("");
  };

  const clear = (key) => {
    setTeam((prev) => ({
      ...prev,
      [key]: { text: "", selected: null },
    }));
    if (activeKey === key) closeSuggestions();
    setWinsResult(null);
    setWinsError("");
  };

  const estimateWins = async () => {
    setWinsLoading(true);
    setWinsError("");
    setWinsResult(null);

    try {
      const hitters = buildHitters(team);
      const starters = buildStarters(team);

      if (hitters.length !== 9) throw new Error("Select all 9 lineup spots (including DH).");
      if (starters.length !== 5) throw new Error("Select all 5 starting pitchers.");

      const result = await fetchTeamWins({ hitters, starters, n_sims: 1500 });
      setWinsResult(result);
    } catch (e) {
      setWinsError(e?.message || "Failed to predict team wins");
    } finally {
      setWinsLoading(false);
    }
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

  {/* CENTERED WINS */}
  <WinsInline
    result={winsResult}
    loading={winsLoading}
    error={winsError}
  />

  <div className="diamondActions">
    <button
      className="btn btnSecondary"
      onClick={estimateWins}
      disabled={!isComplete || winsLoading}
    >
      {winsLoading ? "Estimating..." : "Estimate Wins"}
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

          {FIELD_POSITIONS.map((p) => (
            <TeamPositionPin
              key={p.key}
              posKey={p.key}
              label={p.label}
              title={p.name}
              className={`pin--${p.key.toLowerCase()}`}
              value={team[p.key].text}
              selected={team[p.key].selected}
              isActive={activeKey === p.key}
              suggestions={activeKey === p.key ? suggestions : []}
              onChangeText={setText}
              onPick={pick}
              onClear={clear}
              onCloseSuggestions={closeSuggestions}
              onActivate={activate}
            />
          ))}
        </div>

        {/* SIDEBAR */}
        <div className="sideStack">
          <TeamWins result={winsResult} loading={winsLoading} error={winsError} />

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

// import React, { useRef, useState } from "react";
// import TeamPositionPin from "../components/TeamPositionPin";
// import RosterCard from "../components/RosterCard";
// import WinsCard from "../components/WinsCard";         
// import { fetchTeamWins } from "../api/teamWins"; 
// import { fetchPitchers } from "../api/pitchers";




// const HITTER_KEYS = ["C","1B","2B","SS","3B","LF","CF","RF","DH"];
// const STARTER_KEYS = ["SP1","SP2","SP3","SP4","SP5"];

// function buildHitters(team) {
//   return HITTER_KEYS.map((k) => team[k]?.selected?.fullName).filter(Boolean);
// }

// function buildStarters(team) {
//   return STARTER_KEYS.map((k) => team[k]?.selected?.fullName).filter(Boolean);
// }

// const FIELD_POSITIONS = [
//   { key: "C",  label: "C",  name: "Catcher" },
//   { key: "1B", label: "1B", name: "First Base" },
//   { key: "2B", label: "2B", name: "Second Base" },
//   { key: "SS", label: "SS", name: "Shortstop" },
//   { key: "3B", label: "3B", name: "Third Base" },
//   { key: "LF", label: "LF", name: "Left Field" },
//   { key: "CF", label: "CF", name: "Center Field" },
//   { key: "RF", label: "RF", name: "Right Field" },
//   { key: "DH", label: "DH", name: "Designated Hitter" },
// ];

// const ROTATION = [
//   { key: "SP1", label: "SP1", name: "Starter 1" },
//   { key: "SP2", label: "SP2", name: "Starter 2" },
//   { key: "SP3", label: "SP3", name: "Starter 3" },
//   { key: "SP4", label: "SP4", name: "Starter 4" },
//   { key: "SP5", label: "SP5", name: "Starter 5" },
// ];

// async function fetchPlayers(q) {
//   const res = await fetch(`http://localhost:5000/api/players?q=${encodeURIComponent(q)}`);
//   if (!res.ok) return [];
//   return await res.json();
// }

// export default function DiamondPage() {
//   const isPitcherSlot = (key) => key.startsWith("SP");
//   const [team, setTeam] = useState(() => {
//     const init = {};
//     for (const p of [...FIELD_POSITIONS, ...ROTATION]) {
//       init[p.key] = { text: "", selected: null };
//     }
//     return init;
//   });

//   const [activeKey, setActiveKey] = useState(null);
//   const [suggestions, setSuggestions] = useState([]);
//   const debounceRef = useRef(null);
//   const [winsLoading, setWinsLoading] = useState(false);
//   const [winsError, setWinsError] = useState("");
//   const [winsResult, setWinsResult] = useState(null);

//   const estimateWins = async () => {
//     setWinsLoading(true);
//     setWinsError("");
//     setWinsResult(null);

//     try {
//       const hitters = buildHitters(team);
//       const starters = buildStarters(team);

//       if (hitters.length !== 9) {
//         throw new Error("Select all 9 lineup spots (including DH) first.");
//       }
//       if (starters.length !== 5) {
//         throw new Error("Select all 5 starting pitchers first.");
//       }

//       const result = await fetchTeamWins({ hitters, starters, n_sims: 1500 });
//       setWinsResult(result);
//     } catch (e) {
//       setWinsError(e.message || "Failed to predict team wins");
//     } finally {
//       setWinsLoading(false);
//     }
//   };

//   const isComplete =
//     FIELD_POSITIONS.every((p) => team[p.key]?.selected) &&
//     ROTATION.every((p) => team[p.key]?.selected);

//   const closeSuggestions = () => {
//     setActiveKey(null);
//     setSuggestions([]);
//   };

//   const setText = (key, value) => {
//     setTeam((prev) => ({
//       ...prev,
//       [key]: { ...prev[key], text: value, selected: null },
//     }));

//     const q = value.trim();
//     if (q.length < 2) {
//       closeSuggestions();
//       return;
//     }

//     setActiveKey(key);

//   if (debounceRef.current) clearTimeout(debounceRef.current);
//   debounceRef.current = setTimeout(async () => {
//     try {
//       const list = isPitcherSlot(key)
//         ? await fetchPitchers(q)
//         : await fetchPlayers(q); // your existing hitter search
//       setSuggestions(list);
//     } catch {
//       setSuggestions([]);
//     }
//   }, 150);
// };


//   const activate = (key, value) => {
//     const q = (value || "").trim();
//     if (q.length >= 2) setActiveKey(key);
//   };

//   const pick = (key, player) => {
//     setTeam((prev) => ({
//       ...prev,
//       [key]: { text: player.fullName, selected: player },
//     }));
//     closeSuggestions();
//     setWinsResult(null);
//     setWinsError("");

//   };

//   const clear = (key) => {
//     setTeam((prev) => ({
//       ...prev,
//       [key]: { text: "", selected: null },
//     }));
//     if (activeKey === key){
//       closeSuggestions();
//       setWinsResult(null);
//     setWinsError("");
// }
//   };

//   const lineupSections = [
//     { title: "Lineup + Defense", positions: FIELD_POSITIONS },
//     { title: "Starting Rotation", positions: ROTATION },
//   ];

//   return (
//     <div className="diamondTab">
//       <div className="diamondHeader">
//         <div>
//           <h2 className="diamondTitle">Build a Team</h2>
//           <p className="diamondSubtitle">
//             Fill defense + DH on the field, and pick 5 starters in the rotation.
//           </p>
//         </div>

//         <div className="diamondActions">
//           <button
//               className="btn btnSecondary"
//               onClick={estimateWins}
//             disabled={!isComplete || winsLoading}>
//                 {winsLoading ? "Estimating..." : "Estimate Wins"}
//           </button>

//           <div className={`teamStatus ${isComplete ? "teamStatus--ready" : ""}`}>
//             {isComplete ? "Team complete ✅" : "Fill all positions"}
//           </div>
//         </div>
//       </div>

//       <div className="diamondWrap">
//         {/* FIELD */}
//         <div className="field">
//           <div className="infield" />
//           <div className="base base--home" title="Home" />
//           <div className="base base--first" title="1st Base" />
//           <div className="base base--second" title="2nd Base" />
//           <div className="base base--third" title="3rd Base" />

//           {/* Diamond pins (NO pitcher pin anymore) */}
//           <TeamPositionPin posKey="C"  label="C"  title="Catcher" className="pin--c"
//             value={team.C.text} selected={team.C.selected}
//             isActive={activeKey === "C"} suggestions={activeKey === "C" ? suggestions : []}
//             onChangeText={setText} onPick={pick} onClear={clear}
//             onCloseSuggestions={closeSuggestions} onActivate={activate}
//           />

//           <TeamPositionPin posKey="1B" label="1B" title="First Base" className="pin--1b"
//             value={team["1B"].text} selected={team["1B"].selected}
//             isActive={activeKey === "1B"} suggestions={activeKey === "1B" ? suggestions : []}
//             onChangeText={setText} onPick={pick} onClear={clear}
//             onCloseSuggestions={closeSuggestions} onActivate={activate}
//           />

//           <TeamPositionPin posKey="2B" label="2B" title="Second Base" className="pin--2b"
//             value={team["2B"].text} selected={team["2B"].selected}
//             isActive={activeKey === "2B"} suggestions={activeKey === "2B" ? suggestions : []}
//             onChangeText={setText} onPick={pick} onClear={clear}
//             onCloseSuggestions={closeSuggestions} onActivate={activate}
//           />

//           <TeamPositionPin posKey="SS" label="SS" title="Shortstop" className="pin--ss"
//             value={team.SS.text} selected={team.SS.selected}
//             isActive={activeKey === "SS"} suggestions={activeKey === "SS" ? suggestions : []}
//             onChangeText={setText} onPick={pick} onClear={clear}
//             onCloseSuggestions={closeSuggestions} onActivate={activate}
//           />

//           <TeamPositionPin posKey="3B" label="3B" title="Third Base" className="pin--3b"
//             value={team["3B"].text} selected={team["3B"].selected}
//             isActive={activeKey === "3B"} suggestions={activeKey === "3B" ? suggestions : []}
//             onChangeText={setText} onPick={pick} onClear={clear}
//             onCloseSuggestions={closeSuggestions} onActivate={activate}
//           />

//           <TeamPositionPin posKey="LF" label="LF" title="Left Field" className="pin--lf"
//             value={team.LF.text} selected={team.LF.selected}
//             isActive={activeKey === "LF"} suggestions={activeKey === "LF" ? suggestions : []}
//             onChangeText={setText} onPick={pick} onClear={clear}
//             onCloseSuggestions={closeSuggestions} onActivate={activate}
//           />

//           <TeamPositionPin posKey="CF" label="CF" title="Center Field" className="pin--cf"
//             value={team.CF.text} selected={team.CF.selected}
//             isActive={activeKey === "CF"} suggestions={activeKey === "CF" ? suggestions : []}
//             onChangeText={setText} onPick={pick} onClear={clear}
//             onCloseSuggestions={closeSuggestions} onActivate={activate}
//           />

//           <TeamPositionPin posKey="RF" label="RF" title="Right Field" className="pin--rf"
//             value={team.RF.text} selected={team.RF.selected}
//             isActive={activeKey === "RF"} suggestions={activeKey === "RF" ? suggestions : []}
//             onChangeText={setText} onPick={pick} onClear={clear}
//             onCloseSuggestions={closeSuggestions} onActivate={activate}
//           />

//           {/* NEW: DH pin */}
//           <TeamPositionPin posKey="DH" label="DH" title="Designated Hitter" className="pin--dh"
//             value={team.DH.text} selected={team.DH.selected}
//             isActive={activeKey === "DH"} suggestions={activeKey === "DH" ? suggestions : []}
//             onChangeText={setText} onPick={pick} onClear={clear}
//             onCloseSuggestions={closeSuggestions} onActivate={activate}
//           />
//         </div>

//         {/* SIDEBAR */}
//         <div className="sideStack">
//           <WinsCard result={winsResult} loading={winsLoading} error={winsError} />  {/* NEW */}
//           <div className="rotationCard card">
//             <div className="rotationTitleRow">
//               <h3 className="rotationTitle">Starting Rotation</h3>
//               <span className="rotationHint">Pick 5 starters</span>
//             </div>

//             <div className="rotationGrid">
//               {ROTATION.map((sp) => (
//                 <TeamPositionPin
//                   key={sp.key}
//                   mode="inline"
//                   posKey={sp.key}
//                   label={sp.label}
//                   title={sp.name}
//                   value={team[sp.key].text}
//                   selected={team[sp.key].selected}
//                   isActive={activeKey === sp.key}
//                   suggestions={activeKey === sp.key ? suggestions : []}
//                   onChangeText={setText}
//                   onPick={pick}
//                   onClear={clear}
//                   onCloseSuggestions={closeSuggestions}
//                   onActivate={activate}
//                 />
//               ))}
//             </div>
//           </div>

//           <RosterCard sections={lineupSections} team={team} />
//         </div>
//       </div>
//     </div>
//   );
// }
