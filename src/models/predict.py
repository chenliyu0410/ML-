"""預測未來 12–24 個月的量 / 值 / 單價。

多步預測有兩種做法，先決定用哪一種再寫程式：

  recursive  用 t 的預測值當作 t+1 的 lag 特徵。可用單一模型，
             但誤差會逐步累積，長期預測會漂。
  direct     為每個 horizon 各訓一個模型（h=1, 2, ..., 12）。
             誤差不累積，但模型數量 × 訓練成本上升。

本專案 horizon 到 12–24 個月，recursive 的累積誤差風險偏高，
建議先用 direct，把 horizon 當成訓練時的一個維度。
"""

from __future__ import annotations


def forecast_recursive(model, last_window, horizon: int):
    """遞迴多步預測。"""
    raise NotImplementedError


def forecast_direct(models: dict, X, horizon: int):
    """直接多步預測：models[h] 對應 horizon h 的模型。"""
    raise NotImplementedError
