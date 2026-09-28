import copy

import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from .model import DualBranchLSTM

device = "cuda" if torch.cuda.is_available() else "cpu"

EPOCHS = 100
BATCH_SIZE = 16
LR = 0.001
WEIGHT_DECAY = 1e-4
PATIENCE = 15  # stop if val_loss hasn't improved in this many epochs


def train_model(train_ds, val_ds, epochs: int = EPOCHS) -> tuple[DualBranchLSTM, list[float], list[float]]:
    model = DualBranchLSTM().to(device)
    criterion = nn.MSELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=LR, weight_decay=WEIGHT_DECAY)

    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=BATCH_SIZE, shuffle=False)

    train_losses, val_losses = [], []
    best_val_loss = float("inf")
    best_state = None
    epochs_since_improvement = 0

    for epoch in range(1, epochs + 1):
        model.train()
        total = 0.0
        for x_short, x_long, y in train_loader:
            x_short, x_long, y = x_short.to(device), x_long.to(device), y.to(device)
            optimizer.zero_grad()
            preds = model(x_short, x_long)
            loss = criterion(preds, y)
            loss.backward()
            optimizer.step()
            total += loss.item()
        train_loss = total / max(len(train_loader), 1)
        train_losses.append(train_loss)

        model.eval()
        vtotal = 0.0
        with torch.no_grad():
            for x_short, x_long, y in val_loader:
                x_short, x_long, y = x_short.to(device), x_long.to(device), y.to(device)
                preds = model(x_short, x_long)
                vtotal += criterion(preds, y).item()
        val_loss = vtotal / max(len(val_loader), 1)
        val_losses.append(val_loss)

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_state = copy.deepcopy(model.state_dict())
            epochs_since_improvement = 0
        else:
            epochs_since_improvement += 1

        if epoch % 10 == 0 or epoch == 1:
            print(f"  epoch {epoch}/{epochs} - train_loss {train_loss:.5f} - val_loss {val_loss:.5f}")

        if epochs_since_improvement >= PATIENCE:
            print(f"  early stop at epoch {epoch} (best val_loss {best_val_loss:.5f})")
            break

    if best_state is not None:
        model.load_state_dict(best_state)

    return model, train_losses, val_losses
