import torch
import torch.nn as nn

HORIZON = 5


class SimpleSeqModel(nn.Module):
    """Single-branch RNN or LSTM reading one window length, predicting HORIZON
    days directly. Deliberately simpler than the site's main TripleBranchLSTM
    (model.py) - this exists purely to compare algorithms fairly, one window
    length at a time, for the Prediction Lab's "LSTM vs RNN" question."""

    def __init__(self, cell_type: str, n_features: int = 2, hidden_dim: int = 32, horizon: int = HORIZON):
        super().__init__()
        cell = nn.LSTM if cell_type == "lstm" else nn.RNN
        self.rnn = cell(n_features, hidden_dim, batch_first=True)
        self.head = nn.Linear(hidden_dim, horizon)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        out, _ = self.rnn(x)
        last = out[:, -1, :]
        return self.head(last)
