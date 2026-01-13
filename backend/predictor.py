import torch
import numpy as np
from model import TabDDPMModel, sample, device
from data_processing import logit, inv_logit, safe_log, safe_exp

UPCOMING_YEAR = 2026
N_SAMPLES = 4096
MIN_PA_FOR_HISTORY = 50

class BaseballPredictor:
    def __init__(self, model_path, cond_scaler, y_scaler, season_stats, people):
        self.model = TabDDPMModel(y_dim=2, cond_dim=4, timeEmbShape=32, hidden=256).to(device)
        checkpoint = torch.load(model_path, map_location=device)
        self.model.load_state_dict(checkpoint['model'])
        self.model.eval()
        
        self.cond_scaler = cond_scaler
        self.y_scaler = y_scaler
        self.season_stats = season_stats
        self.people = people
    
    def get_player_id(self, full_name):
        first, last = full_name.split(" ", 1)
        row = self.people[(self.people["nameFirst"] == first) & (self.people["nameLast"] == last)]
        if row.empty:
            raise ValueError(f"No player found for name: {full_name}")
        return row.iloc[0]["playerID"]
    
    def summarize_dist(self, x):
        return {
            "mean": float(np.mean(x)),
            "p10": float(np.quantile(x, 0.10)),
            "p25": float(np.quantile(x, 0.25)),
            "p50": float(np.quantile(x, 0.50)),
            "p75": float(np.quantile(x, 0.75)),
            "p90": float(np.quantile(x, 0.90)),
        }
    
    @torch.no_grad()
    def predict(self, full_name):
        playerID = self.get_player_id(full_name)
        
        hist = self.season_stats[
            (self.season_stats["playerID"] == playerID) &
            (self.season_stats["yearID"] < UPCOMING_YEAR)
        ].sort_values("yearID")
        
        if hist.empty:
            raise ValueError(f"No history for {full_name} before {UPCOMING_YEAR}")
        
        hist_pa = hist[hist["PA"] >= MIN_PA_FOR_HISTORY]
        last = hist_pa.iloc[-1] if not hist_pa.empty else hist.iloc[-1]
        
        prev_year = int(last["yearID"])
        age_next = float(last["age"] + (UPCOMING_YEAR - prev_year))
        
        prev_obp = float(last["OBP"])
        prev_slg = float(last["SLG"])
        prev_pa = float(last["PA"])
        
        prev_zobp = float(logit(np.array([prev_obp]))[0])
        prev_lslg = float(safe_log(np.array([prev_slg]))[0])
        
        cond_raw = np.array([[prev_zobp, prev_lslg, prev_pa, age_next]], dtype=np.float32)
        cond_scaled = self.cond_scaler.transform(cond_raw)
        
        cond = torch.tensor(
            np.repeat(cond_scaled, N_SAMPLES, axis=0),
            dtype=torch.float32,
            device=device
        )
        
        y_scaled = sample(self.model, cond, clip_x0=3.0).cpu().numpy()
        y_delta = self.y_scaler.inv(y_scaled)
        
        d_zobp = y_delta[:, 0]
        d_logslg = y_delta[:, 1]
        
        zobp_next = prev_zobp + d_zobp
        obp_next = inv_logit(zobp_next)
        
        logslg_next = prev_lslg + d_logslg
        slg_next = safe_exp(logslg_next)
        
        obp_next = np.clip(obp_next, 0.0, 1.0)
        slg_next = np.clip(slg_next, 0.0, 2.0)
        ops_next = obp_next + slg_next
        
        return {
            "name": full_name,
            "playerID": playerID,
            "upcoming_year": UPCOMING_YEAR,
            "condition_used": {
                "prev_year": prev_year,
                "prev_OBP": prev_obp,
                "prev_SLG": prev_slg,
                "prev_PA": int(prev_pa),
                "age_next": age_next,
            },
            "OBP": self.summarize_dist(obp_next),
            "SLG": self.summarize_dist(slg_next),
            "OPS": self.summarize_dist(ops_next),
        }