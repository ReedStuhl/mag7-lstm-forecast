import torch
import torch.nn as nn

SHORT_WINDOW = 5     # trading days (~1 trading week)
MEDIUM_WINDOW = 15    # trading days (~3 trading weeks)
LONG_WINDOW = 30      # trading days (~6 weeks)
HORIZON = 5           # trading days predicted (Mon-Fri)
N_FEATURES = 2        # close (scaled), log_return


class TripleBranchLSTM(nn.Module):
    """Three LSTM branches read the same feature series at three lookback
    lengths (short-term momentum, a multi-week view, and a ~6-week view);
    their final hidden states are concatenated and mapped to a 5-value
    (Mon-Fri) forecast. Renamed from DualBranchLSTM when a third (30-day)
    branch was added alongside the existing 5-day and 15-day ones."""

    def __init__(self, n_features: int = N_FEATURES, hidden_dim: int = 32, horizon: int = HORIZON):
        super().__init__()
        self.short_lstm = nn.LSTM(n_features, hidden_dim, batch_first=True)
        self.medium_lstm = nn.LSTM(n_features, hidden_dim, batch_first=True)
        self.long_lstm = nn.LSTM(n_features, hidden_dim, batch_first=True)
        self.head = nn.Sequential(
            nn.Linear(hidden_dim * 3, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, horizon),
        )

    def forward(
        self, x_short: torch.Tensor, x_medium: torch.Tensor, x_long: torch.Tensor
    ) -> torch.Tensor:
        _, (h_short, _) = self.short_lstm(x_short)
        _, (h_medium, _) = self.medium_lstm(x_medium)
        _, (h_long, _) = self.long_lstm(x_long)
        fused = torch.cat([h_short[-1], h_medium[-1], h_long[-1]], dim=-1)
        return self.head(fused)
