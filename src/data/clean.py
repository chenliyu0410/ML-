"""清理：單位統一、國名標準化、零值補齊、離群值標記。

輸出 data/processed 的長格式 panel，唯一鍵為 (ym, hs_code, country)。

為什麼一定要用月資料：年度資料從 2015 年起只有約 10 個點，任何 ML 模型都
無法訓練。改為 月 × 稅號 × 國家 的 panel 後，樣本數可從 10 筆放大到數萬筆。
"""

from __future__ import annotations

import pandas as pd


def standardize_country(df: pd.DataFrame, mapping: dict[str, str]) -> pd.DataFrame:
    """國名標準化。

    中國大陸 / 中國 / CHINA、美國 / USA 等寫法不一致，需建對照表。
    TODO: 對照表建在 config/country_map.yaml，未命中的國名要 warn 而非靜默通過。
    """
    raise NotImplementedError


def fill_zero_months(df: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    """補齊沒有交易的月份。

    某月某國沒有進口 → 應補 0 而非 NaN。留 NaN 會讓 lag 特徵斷裂，
    模型看到的「上個月」其實跳過了空月，等於偷偷改了時間軸。

    TODO: 以完整的 ym × hs_code × country 笛卡兒積 reindex 後 fillna(0)。
    """
    raise NotImplementedError


def drop_sparse(df: pd.DataFrame, min_months: int, strategy: str) -> pd.DataFrame:
    """處理稀疏序列。

    交易月數 < min_months 的「國家 × 品項」組合先剔除或併入「其他」。
    TODO: merge_to_other 時要保留原始明細以便回溯。
    """
    raise NotImplementedError


def flag_outliers(df: pd.DataFrame, col: str, k: float) -> pd.DataFrame:
    """IQR 標記離群值 —— 標記，不刪除。

    單筆超大金額可能是轉口或報關異常。先查原因再決定怎麼處理，
    直接刪掉等於把真實事件從資料裡抹掉。
    """
    raise NotImplementedError


def add_unit_price(df: pd.DataFrame) -> pd.DataFrame:
    """計算核心衍生欄位 unit_price = value_usd / weight_kg。

    TODO: weight_kg 為 0 的列會產生 inf，需明確處理（設 NaN 並記錄筆數）。
    """
    raise NotImplementedError


def deflate(df: pd.DataFrame, index: pd.Series, base_period: str) -> pd.DataFrame:
    """以 IPI / CPI 平減，產出 unit_price_real。

    這是 Phase 1 假設驗證的關鍵：名目單價上升可能只是通膨，
    要看實質單價才知道是不是真的精緻化。
    """
    raise NotImplementedError
