import torch
import torch.nn as nn

SHORT_WINDOW = 10   # trading days
LONG_WINDOW = 25    # trading days (~1 trading month)
HORIZON = 5          # trading days predicted (Mon-Fri)
N_FEATURES = 2        # close (scaled), log_return


class DualBranchLSTM(nn.Module):
    """Two LSTM branches read the same feature series at different lookback
    lengths (short-term momentum vs ~monthly cycle); their final hidden
    states are concatenated and mapped to a 5-value (Mon-Fri) forecast."""

    def __init__(self, n_features: int = N_FEATURES, hidden_dim: int = 32, horizon: int = HORIZON):
        super().__init__()
        self.short_lstm = nn.LSTM(n_features, hidden_dim, batch_first=True)
        self.long_lstm = nn.LSTM(n_features, hidden_dim, batch_first=True)
        self.head = nn.Sequential(
            nn.Linear(hidden_dim * 2, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, horizon),
        )

    def forward(self, x_short: torch.Tensor, x_long: torch.Tensor) -> torch.Tensor:
        _, (h_short, _) = self.short_lstm(x_short)
        _, (h_long, _) = self.long_lstm(x_long)
        fused = torch.cat([h_short[-1], h_long[-1]], dim=-1)
        return self.head(fused)
