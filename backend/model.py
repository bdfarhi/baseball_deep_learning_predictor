import math
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Noise schedule
Time = 100
b = torch.linspace(1e-4, 1e-2, Time, device=device)
a = 1.0 - b
alpha_bar = torch.cumprod(a, dim=0)

sqrt_ab = torch.sqrt(alpha_bar)
sqrt_1m_ab = torch.sqrt(1.0 - alpha_bar)
sqrt_recip_a = torch.sqrt(1.0 / a)

alpha_bar_prev = torch.cat([torch.ones(1, device=device), alpha_bar[:-1]])
posterior_var = b * (1.0 - alpha_bar_prev) / (1.0 - alpha_bar)

def _extract(arr_1d, t, ndim):
    return arr_1d[t].view(t.shape[0], *([1]*(ndim-1)))

# Model Architecture
class SinusoidalTimeEmbedding(nn.Module):
    def __init__(self, dim):
        super().__init__()
        self.dim = dim
    
    def forward(self, t):
        half = self.dim // 2
        freqs = torch.exp(-math.log(10000) * torch.arange(0, half, device=t.device).float() / (half - 1))
        args = t.float().unsqueeze(1) * freqs.unsqueeze(0)
        emb = torch.cat([torch.sin(args), torch.cos(args)], dim=1)
        if self.dim % 2 == 1:
            emb = torch.cat([emb, torch.zeros((t.shape[0],1), device=t.device)], dim=1)
        return emb

class TabDDPMModel(nn.Module):
    def __init__(self, y_dim=2, cond_dim=4, timeEmbShape=32, hidden=256):
        super().__init__()
        self.timeEmbedding = nn.Sequential(
            SinusoidalTimeEmbedding(timeEmbShape),
            nn.Linear(timeEmbShape, timeEmbShape),
            nn.ReLU()
        )
        self.net = nn.Sequential(
            nn.Linear(y_dim + cond_dim + timeEmbShape, hidden),
            nn.ReLU(),
            nn.Linear(hidden, hidden),
            nn.ReLU(),
            nn.Linear(hidden, hidden),
            nn.ReLU(),
            nn.Linear(hidden, y_dim)
        )

    def forward(self, y_t, t, cond):
        tEmb = self.timeEmbedding(t)
        x = torch.cat([y_t, cond, tEmb], dim=1)
        return self.net(x)

@torch.no_grad()
def sample(model, cond, clip_x0=3.0):
    model.eval()
    B = cond.shape[0]
    y = torch.randn((B, 2), device=device)
    
    for i in range(Time - 1, -1, -1):
        t = torch.full((B,), i, device=device, dtype=torch.long)
        eps = model(y, t, cond)
        ab_t = _extract(alpha_bar, t, y.ndim)
        sab_t = torch.sqrt(ab_t)
        s1m_t = torch.sqrt(1.0 - ab_t)

        x0 = (y - s1m_t * eps) / (sab_t + 1e-8)

        if clip_x0 is not None:
            x0 = torch.clamp(x0, -clip_x0, clip_x0)

        if i == 0:
            y = x0
        else:
            t_prev = torch.full((B,), i - 1, device=device, dtype=torch.long)
            ab_prev = _extract(alpha_bar, t_prev, y.ndim)
            y = torch.sqrt(ab_prev) * x0 + torch.sqrt(1.0 - ab_prev) * eps
    
    return y