"""視覺化。

Phase 1 的兩張圖是整個專案的門面：
  1. 實質單價指數趨勢 + 對照組（一般食品）—— 精緻化假設成立與否看這張
  2. 高單價高成長象限圖 —— 採購建議名單的來源
"""

from __future__ import annotations


def plot_unit_price_trend(df, control_df=None):
    """名目 vs 實質單價趨勢，疊上對照組。

    唯有寵物食品的實質單價漲幅顯著高於整體食品，精緻化的結論才成立。
    圖上要標出 HS 改版年度（2017 / 2022）的垂直線，讓斷點無所遁形。
    """
    raise NotImplementedError


def plot_quadrant(cluster_df):
    """單價水位 × 成長率象限圖，標出高單價高成長群。"""
    raise NotImplementedError


def plot_forecast_vs_baseline(y_true, y_pred, y_baseline):
    """預測 vs 實際 vs baseline —— 三條線畫在一起，贏沒贏一眼看得出來。"""
    raise NotImplementedError


def plot_feature_importance(model, feature_names, top_n: int = 30):
    """特徵重要度排序（可解釋性產出）。

    建議用 SHAP 而非 LightGBM 內建 gain：內建重要度對高基數類別變數
    （country）有偏誤，會高估其重要性。
    """
    raise NotImplementedError
