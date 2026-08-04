"""特徵工程的防洩漏測試。

這幾個測試不是形式。資料洩漏的特徵是「回測分數好得不合理，上線就崩」，
而且不會拋錯 —— 唯一能擋住它的就是明確斷言時點 t 的特徵沒看到 t 的值。
"""

from __future__ import annotations

import pandas as pd
import pytest

from src.features import build_features as bf


@pytest.fixture
def panel() -> pd.DataFrame:
    """兩個國家各 6 個月的最小 panel，數值刻意好認。"""
    rows = []
    for country, base in [("USA", 100), ("JPN", 200)]:
        for i in range(6):
            rows.append(
                {
                    "ym": pd.Timestamp(2020, 1, 1) + pd.DateOffset(months=i),
                    "hs_code": "2309.10",
                    "country": country,
                    "unit_price": base + i,
                    "value_usd": (base + i) * 10,
                    "weight_kg": 10.0,
                }
            )
    return pd.DataFrame(rows)


def test_lag_shifts_within_entity(panel):
    """lag 必須在同一個國家內位移，不可跨國家取值。"""
    out = bf.add_lags(panel, ["unit_price"], [1])
    usa = out[out.country == "USA"].reset_index(drop=True)
    jpn = out[out.country == "JPN"].reset_index(drop=True)

    # 每個實體的第一列沒有前期，必須是 NaN
    assert pd.isna(usa.loc[0, "unit_price_lag_1"])
    assert pd.isna(jpn.loc[0, "unit_price_lag_1"])
    # JPN 第一列不可以撿到 USA 最後一列的值
    assert jpn.loc[0, "unit_price_lag_1"] != 105


def test_rolling_excludes_current_period(panel):
    """時點 t 的 rolling 不可包含 t 自己 —— 少了 shift(1) 就是洩漏。"""
    out = bf.add_rolling(panel, ["unit_price"], [3], ["mean"])
    usa = out[out.country == "USA"].reset_index(drop=True)

    # USA 單價為 100,101,102,103,104,105
    # 第 4 列（index 3, 值 103）的 roll_mean_3 應為 (100+101+102)/3 = 101
    assert usa.loc[3, "unit_price_roll_mean_3"] == pytest.approx(101.0)
    # 若含當期會是 (101+102+103)/3 = 102
    assert usa.loc[3, "unit_price_roll_mean_3"] != pytest.approx(102.0)


def test_share_sums_to_one_per_month(panel):
    """同月同稅號的市占率總和應為 1。"""
    out = bf.add_market_structure(panel)
    totals = out.groupby("ym")["share"].sum()
    assert totals.round(6).eq(1.0).all()


def test_regulatory_flag_marks_only_restricted(panel):
    """MP1 管制旗標只能標到受管制的來源國。

    誤標會讓沒受管制的國家被排除在採購建議之外；漏標則會讓中國的
    低進口量被讀成市場偏好，而不是法規限制。
    """
    panel.loc[panel.country == "JPN", "country"] = "中國大陸"
    out = bf.add_regulatory_flags(panel, ["中國大陸"])

    assert out.loc[out.country == "中國大陸", "is_regulated_source"].eq(1).all()
    assert out.loc[out.country == "USA", "is_regulated_source"].eq(0).all()


def test_growth_no_inf_on_zero_months(panel):
    """補 0 的月份不可產生 inf —— inf 流進模型會讓訓練直接爆掉。"""
    panel.loc[panel.index[0], "unit_price"] = 0.0
    out = bf.add_growth(panel, ["unit_price"])
    import numpy as np

    assert not np.isinf(out["unit_price_mom"].to_numpy(dtype=float)).any()
