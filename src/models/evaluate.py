"""統一評估函式 —— 所有模型都必須跟 baseline 比。

Baseline 不是形式。實務上很多時間序列專案的複雜模型打不贏 Seasonal Naive。
若 LightGBM 沒有明顯優於 baseline，那個結論本身就要誠實寫進報告 ——
比硬凹一個好看的數字有價值。
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def mae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.mean(np.abs(y_true - y_pred)))


def rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.sqrt(np.mean((y_true - y_pred) ** 2)))


def smape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """對稱 MAPE。

    MAPE 在實際值接近 0 時會爆炸，稀疏序列（很多月份補 0）一定要避開。
    分母同為 0 的點視為誤差 0，不計入懲罰。
    """
    denom = (np.abs(y_true) + np.abs(y_pred)) / 2
    ratio = np.divide(
        np.abs(y_true - y_pred), denom, out=np.zeros_like(denom, dtype=float), where=denom > 0
    )
    return float(np.mean(ratio) * 100)


def mase(y_true: np.ndarray, y_pred: np.ndarray, y_train: np.ndarray, season: int = 12) -> float:
    """MASE：以訓練集的 seasonal naive 誤差為尺度。

    < 1 代表打贏 seasonal naive，> 1 代表打輸。這個指標的好處是
    「有沒有贏 baseline」直接寫在數值上，不用另外算改善率。
    """
    scale = np.mean(np.abs(y_train[season:] - y_train[:-season]))
    if scale == 0:
        return float("nan")
    return float(np.mean(np.abs(y_true - y_pred)) / scale)


def naive_forecast(series: pd.Series) -> pd.Series:
    """預測值 = 上期值。"""
    return series.shift(1)


def seasonal_naive_forecast(series: pd.Series, season: int = 12) -> pd.Series:
    """預測值 = 去年同月值 —— 有季節性時很難打敗。"""
    return series.shift(season)


def report(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_baseline: np.ndarray,
    y_train: np.ndarray | None = None,
) -> dict[str, float]:
    """輸出模型指標與相對 baseline 的改善率。

    improvement_pct 為正代表贏過 baseline。這一欄是報告裡最該被看見的數字，
    絕對誤差好不好看是其次。
    """
    model_mae = mae(y_true, y_pred)
    base_mae = mae(y_true, y_baseline)
    out = {
        "mae": model_mae,
        "rmse": rmse(y_true, y_pred),
        "smape": smape(y_true, y_pred),
        "baseline_mae": base_mae,
        "improvement_pct": (base_mae - model_mae) / base_mae * 100 if base_mae else float("nan"),
    }
    if y_train is not None:
        out["mase"] = mase(y_true, y_pred, y_train)
    return out
