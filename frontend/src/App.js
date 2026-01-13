import React, { useState } from "react";
import "./App.css";

import Tabs from "./components/Tabs";
import PredictionsPage from "./pages/PredictionPage";
import DiamondPage from "./pages/DiamondPage";

export default function App() {
  const [activeTab, setActiveTab] = useState("predict"); // 'predict' | 'diamond'

  return (
    <div className="page">
      <div className="container">
        <div className="header">
          <h1 className="title">Baseball Performance Predictor</h1>
          <p className="subtitle">2026 Season Projections</p>
        </div>

        <Tabs
          activeTab={activeTab}
          onChange={setActiveTab}
          tabs={[
            { key: "predict", label: "Predictions" },
            { key: "diamond", label: "Build a Team" },
          ]}
        />

        {activeTab === "predict" ? <PredictionsPage /> : <DiamondPage />}
      </div>
    </div>
  );
}

