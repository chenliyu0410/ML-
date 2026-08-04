"""特徵工程：lag / rolling / 成長率 / 季節性 / 市場結構 / 外部變數。

╔═══════════════════════════════════════════════════════════════════╗
║ 防資料洩漏是本模組唯一的鐵律                                        ║
║                                                                   ║
║ 所有特徵在時點 t 只能看到 t-1 以前的資料。本模組的做法是：           ║
║   1. 一律先 groupby(entity) 再 shift —— 不同國家的序列不可互相污染   ║
║   2. rolling 之前先 shift(1) —— 否則 t 的 rolling_mean 含 t 自己     ║
║   3. 標準化與 Target Encoding 不在這裡做，一律封裝進 Pipeline，      ║
║      只用訓練集擬合參數                                            ║
╚═══════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# panel 的實體鍵：一個「國家 × 品項」就是一條獨立時間序列
ENTITY = ["hs_code", "country"]
TIME = "ym"


def _sorted_panel(df: pd.DataFrame) -> pd.DataFrame:
    """確保依實體與時間排序 —— shift/rolling 的正確性完全依賴這個前提。"""
    return df.sort_values(ENTITY + [TIME]).reset_index(drop=True)


def add_lags(df: pd.DataFrame, cols: list[str], lags: list[int]) -> pd.DataFrame:
    """加入落後項 lag_1, lag_2, ..."""
    df = _sorted_panel(df)
    g = df.groupby(ENTITY, observed=True)
    for col in cols:
        for lag in lags:
            df[f"{col}_lag_{lag}"] = g[col].shift(lag)
    return df


def add_rolling(
    df: pd.DataFrame,
    cols: list[str],
    windows: list[int],
    stats: list[str],
) -> pd.DataFrame:
    """滾動統計 —— 捕捉趨勢與波動度。

    先 shift(1) 再 rolling：時點 t 的 rolling_mean_3 是 t-3~t-1 的平均，
    不含 t 自己。少了這個 shift 就是把答案餵給模型。
    """
    df = _sorted_panel(df)
    g = df.groupby(ENTITY, observed=True)
    for col in cols:
        shifted = g[col].shift(1)
        for w in windows:
            roll = shifted.groupby([df[c] for c in ENTITY], observed=True).rolling(
                window=w, min_periods=max(2, w // 2)
            )
            for stat in stats:
                df[f"{col}_roll_{stat}_{w}"] = (
                    getattr(roll, stat)().reset_index(level=list(range(len(ENTITY))), drop=True)
                )
    return df


def add_growth(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """成長率：MoM、YoY、12 個月 CAGR。

    用 shift 相除而非 pct_change()，避免補 0 的月份製造 inf。
    """
    df = _sorted_panel(df)
    g = df.groupby(ENTITY, observed=True)
    for col in cols:
        prev_1 = g[col].shift(1)
        prev_12 = g[col].shift(12)
        df[f"{col}_mom"] = _safe_ratio(df[col], prev_1) - 1
        df[f"{col}_yoy"] = _safe_ratio(df[col], prev_12) - 1
        df[f"{col}_cagr_12"] = _safe_ratio(df[col], prev_12) ** (1 / 12) - 1
    return df


def _safe_ratio(num: pd.Series, den: pd.Series) -> pd.Series:
    """分母為 0 或負值時回 NaN，不要讓 inf 流進模型。"""
    den = den.where(den > 0)
    return num / den


def add_seasonal(df: pd.DataFrame, cyclical: bool = True) -> pd.DataFrame:
    """季節性：month / quarter，以及月份的 sin/cos 週期編碼。

    週期編碼讓 12 月與 1 月在特徵空間裡相鄰，樹模型與線性模型都受用。
    """
    ym = pd.to_datetime(df[TIME])
    df["month"] = ym.dt.month
    df["quarter"] = ym.dt.quarter
    if cyclical:
        df["month_sin"] = np.sin(2 * np.pi * df["month"] / 12)
        df["month_cos"] = np.cos(2 * np.pi * df["month"] / 12)
    return df


def add_market_structure(df: pd.DataFrame, value_col: str = "value_usd") -> pd.DataFrame:
    """市場結構：該國市占率、市占變化、HHI 集中度。

    市占以「同月同稅號」為分母 —— 這是同期橫斷面資訊，不是未來資訊，
    不構成洩漏。但 share_delta 用到 shift，仍須 groupby 實體。
    """
    df = _sorted_panel(df)
    total = df.groupby([TIME, "hs_code"], observed=True)[value_col].transform("sum")
    df["share"] = _safe_ratio(df[value_col], total)
    df["share_delta"] = df["share"] - df.groupby(ENTITY, observed=True)["share"].shift(1)

    hhi = (
        df.assign(_sq=df["share"] ** 2)
        .groupby([TIME, "hs_code"], observed=True)["_sq"]
        .transform("sum")
    )
    df["hhi"] = hhi
    return df


def add_regulatory_flags(
    df: pd.DataFrame,
    restricted_countries: list[str],
    flag_col: str = "is_regulated_source",
) -> pd.DataFrame:
    """標記受法規管制的來源國（MP1）。

    中國大陸僅開放「乾狗糧（牛肉口味）」一項，進口量天生受管制壓抑。
    這是結構性因素，不是市場偏好。

    這個 flag 有兩個用途：
      1. 當特徵，讓模型知道這些序列受外生限制
      2. 解讀時的護欄 —— 特徵重要度若顯示 country=中國大陸 很重要，
         要先確認模型是在學管制，而不是在學消費者偏好

    分群時建議依 params.regulatory.exclude_from_clustering 排除這些來源：
    把受管制國家放進「低價衰退」象限並建議「不值得採購」，
    那個建議建立在錯誤的因果上。
    """
    df = df.copy()
    df[flag_col] = df["country"].isin(restricted_countries).astype(int)
    return df


def add_external(df: pd.DataFrame, external: pd.DataFrame) -> pd.DataFrame:
    """併入外部變數：USD/TWD 匯率、CPI、玉米/雞肉價格、SCFI 運價。

    TODO: 外部變數本身也有發布時滯 —— 某月的 CPI 通常下個月才公布。
    要用當月值就等於假設「預測當下已知當月 CPI」，實務上不成立。
    建議一律 shift(1) 或改用預測值，並在報告中明講這個假設。
    """
    raise NotImplementedError


def add_event_dummies(df: pd.DataFrame, events: dict) -> pd.DataFrame:
    """事件 dummy：COVID 期間、貿易協定生效、稅則改版年度。"""
    raise NotImplementedError


def build(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """依 config/params.yaml 的 features 區塊組出完整特徵表。"""
    f = cfg["features"]
    target_cols = ["value_usd", "weight_kg", "unit_price"]

    df = add_lags(df, target_cols, f["lags"])
    df = add_rolling(df, target_cols, f["rolling_windows"], f["rolling_stats"])
    df = add_growth(df, target_cols)
    df = add_seasonal(df, cyclical=f["seasonal"]["cyclical_encoding"])
    df = add_market_structure(df)

    if f["event_dummies"].get("mp1_regulated"):
        reg = cfg["regulatory"]
        df = add_regulatory_flags(df, reg["mp1_restricted_countries"], reg["mp1_flag_col"])
    return df
