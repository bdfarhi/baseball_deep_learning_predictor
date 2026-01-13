import os
import math
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader
from torch.optim import Adam
import pickle

from model import TabDDPMModel, device, Time, alpha_bar, sqrt_ab, sqrt_1m_ab, _extract
from data_processing import (
    compute_season_obp_slg, 
    get_age_of_players, 
    ZScaler,
    logit,
    safe_log
)

# Create models directory if it doesn't exist
os.makedirs('../models', exist_ok=True)

print("Loading data...")
batting = pd.read_csv('../data/Batting.csv')
people = pd.read_csv('../data/People.csv')

print("Computing season stats...")
season_stats = compute_season_obp_slg(batting)
season_stats = get_age_of_players(season_stats, people)

def make_conditional(data, min_pa=400, require_consecutive=True):
    df = data.sort_values(["playerID", "yearID"]).copy()
    
    df["prev_OBP"] = df.groupby("playerID")["OBP"].shift(1)
    df["prev_SLG"] = df.groupby("playerID")["SLG"].shift(1)
    df["prev_PA"] = df.groupby("playerID")["PA"].shift(1)
    df["prev_year"] = df.groupby("playerID")["yearID"].shift(1)
    
    out = df.dropna(subset=["prev_OBP", "prev_SLG", "prev_PA", "prev_year"]).copy()
    
    if require_consecutive:
        out = out[out["prev_year"] == out["yearID"] - 1].copy()
    
    out = out[(out["PA"] >= min_pa) & (out["prev_PA"] >= min_pa)].copy()
    
    return out

def add_transformed_columns(df):
    df = df.copy()
    df["zOBP"] = logit(df["OBP"].to_numpy())
    df["prev_zOBP"] = logit(df["prev_OBP"].to_numpy())
    df["logSLG"] = safe_log(df["SLG"].to_numpy())
    df["prev_logSLG"] = safe_log(df["prev_SLG"].to_numpy())
    df["d_zOBP"] = df["zOBP"] - df["prev_zOBP"]
    df["d_logSLG"] = df["logSLG"] - df["prev_logSLG"]
    return df

print("Creating conditional data...")
cond_all = make_conditional(season_stats, min_pa=400, require_consecutive=True)
print(f"Total conditional rows: {len(cond_all)}")

# Train/validation split
TRAIN_END_YEAR = 2024
VAL_YEAR = 2025
EXCLUDE_YEAR = 2020

train_df = cond_all[
    (cond_all["yearID"] <= TRAIN_END_YEAR) & 
    (cond_all["yearID"] != EXCLUDE_YEAR)
].copy()

val_df = cond_all[cond_all["yearID"] == VAL_YEAR].copy()

print(f"Train rows: {len(train_df)}, Val rows: {len(val_df)}")

# Add transformed columns
train_df = add_transformed_columns(train_df)
val_df = add_transformed_columns(val_df) if len(val_df) else val_df

# Define columns
cond_cols = ["prev_zOBP", "prev_logSLG", "prev_PA", "age"]
y_cols = ["d_zOBP", "d_logSLG"]

# Fit scalers
print("Fitting scalers...")
cond_scaler = ZScaler().fit(train_df[cond_cols].to_numpy(np.float32))
y_scaler = ZScaler().fit(train_df[y_cols].to_numpy(np.float32))

# Transform data
cond_train = cond_scaler.transform(train_df[cond_cols].to_numpy(np.float32))
y_train = y_scaler.transform(train_df[y_cols].to_numpy(np.float32))

if len(val_df):
    cond_val = cond_scaler.transform(val_df[cond_cols].to_numpy(np.float32))
    y_val = y_scaler.transform(val_df[y_cols].to_numpy(np.float32))
else:
    cond_val, y_val = None, None
    print("No 2025 data yet - using 2024 for validation")

# Save scalers
print("Saving scalers...")
with open('../models/cond_scaler.pkl', 'wb') as f:
    pickle.dump(cond_scaler, f)
with open('../models/y_scaler.pkl', 'wb') as f:
    pickle.dump(y_scaler, f)

# Dataset
class SeasonDataset(Dataset):
    def __init__(self, y, cond):
        self.y = torch.tensor(y, dtype=torch.float32)
        self.cond = torch.tensor(cond, dtype=torch.float32)
    
    def __len__(self):
        return self.y.shape[0]
    
    def __getitem__(self, idx):
        return self.y[idx], self.cond[idx]

train_ds = SeasonDataset(y_train, cond_train)
val_ds = SeasonDataset(y_val, cond_val) if y_val is not None else None

BATCH_SIZE = 512
train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True, drop_last=True)
val_loader = DataLoader(val_ds, batch_size=BATCH_SIZE, shuffle=False) if val_ds else None

print(f"Train batches: {len(train_loader)}")
if val_loader:
    print(f"Val batches: {len(val_loader)}")

# Loss function
def ddpm_loss(model, y0, t, cond):
    noise = torch.randn_like(y0)
    at = _extract(sqrt_ab, t, y0.ndim)
    oneMinAt = _extract(sqrt_1m_ab, t, y0.ndim)
    y_t = at * y0 + oneMinAt * noise
    pred = model(y_t, t, cond)
    return F.mse_loss(pred, noise)

# Initialize model
print("Initializing model...")
model = TabDDPMModel(y_dim=2, cond_dim=4, timeEmbShape=32, hidden=256).to(device)
optimizer = Adam(model.parameters(), lr=1e-4)

# Training
EPOCHS = 1000
SAVE_EVERY = 50

print(f"\nStarting training for {EPOCHS} epochs...")
print("=" * 60)

best_val_loss = float('inf')

for epoch in range(EPOCHS):
    # Training
    model.train()
    train_loss = 0.0
    
    for y0, cond in train_loader:
        y0 = y0.to(device)
        cond = cond.to(device)
        bs = y0.size(0)
        t = torch.randint(0, Time, (bs,), device=device).long()
        
        optimizer.zero_grad()
        loss = ddpm_loss(model, y0, t, cond)
        loss.backward()
        optimizer.step()
        train_loss += loss.item()
    
    train_avg = train_loss / len(train_loader)
    
    # Validation
    val_avg = 0.0
    if val_loader:
        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for y0, cond in val_loader:
                y0 = y0.to(device)
                cond = cond.to(device)
                bs = y0.size(0)
                t = torch.randint(0, Time, (bs,), device=device).long()
                val_loss += ddpm_loss(model, y0, t, cond).item()
        val_avg = val_loss / len(val_loader)
    
    # Print progress
    if val_loader:
        print(f"Epoch {epoch:4d} | Train Loss: {train_avg:.4f} | Val Loss: {val_avg:.4f}")
    else:
        print(f"Epoch {epoch:4d} | Train Loss: {train_avg:.4f}")
    
    # Save checkpoint
    if (epoch % SAVE_EVERY == 0) or (epoch == EPOCHS - 1):
        checkpoint = {
            'epoch': epoch,
            'model': model.state_dict(),
            'optimizer': optimizer.state_dict(),
            'train_loss': train_avg,
            'val_loss': val_avg if val_loader else None
        }
        
        checkpoint_path = f'../models/epoch_{epoch:04d}.pt'
        torch.save(checkpoint, checkpoint_path)
        print(f"  → Saved checkpoint: {checkpoint_path}")
        
        # Save as best model if validation loss improved
        if val_loader and val_avg < best_val_loss:
            best_val_loss = val_avg
            torch.save(checkpoint, '../models/best_model.pt')
            print(f"  → New best model! Val loss: {val_avg:.4f}")

# Save final model
final_checkpoint = {
    'epoch': EPOCHS - 1,
    'model': model.state_dict(),
    'optimizer': optimizer.state_dict(),
    'train_loss': train_avg,
    'val_loss': val_avg if val_loader else None
}
torch.save(final_checkpoint, '../models/best_model.pt')

print("\n" + "=" * 60)
print("Training complete!")
print(f"Final model saved to: ../models/best_model.pt")
print(f"Scalers saved to: ../models/cond_scaler.pkl and ../models/y_scaler.pkl")
print("=" * 60)