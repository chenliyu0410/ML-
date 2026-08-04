"""設定檔載入。

所有參數集中在 config/ 底下，程式碼裡不要出現 magic number。
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = PROJECT_ROOT / "config"


@lru_cache(maxsize=None)
def load(name: str = "params") -> dict[str, Any]:
    """載入 config/<name>.yaml。

    Args:
        name: 檔名（不含副檔名），例如 "params" 或 "hs_codes"。
    """
    path = CONFIG_DIR / f"{name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"找不到設定檔：{path}")
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def resolve(relative: str) -> Path:
    """把 config 裡的相對路徑轉成專案根目錄下的絕對路徑。"""
    return PROJECT_ROOT / relative


def _confirmed_items() -> list[dict[str, Any]]:
    """已確認納入的號列項目。

    只取 status == "confirmed"。待查證（pending）的項目不會出現在這裡 ——
    這是刻意的：號列沒查證完就開始建模，等於整份分析建在流沙上。
    """
    cfg = load("hs_codes")
    return [
        item for item in cfg.get("include", []) if item.get("status") == "confirmed"
    ]


def included_hs_codes() -> list[str]:
    """回傳已確認納入的 CCC 號列（顯示格式，如 2309.10.00.00-2）。"""
    return [item["code"] for item in _confirmed_items()]


def hs_query_string() -> str:
    """產生單一窗口「指定貨品號列」欄位要貼的字串。

    格式為無分隔符的 11 碼，以逗號串接：
        23091000002,42050090104

    人工下載時**不要手打這串**。打錯一碼查出來的是完全不同的貨品，
    而且不會報錯 —— 你會拿到一份看起來正常但完全錯誤的資料。
    用這個函式產生後複製貼上。
    """
    codes = [item["code_query"] for item in _confirmed_items()]
    _assert_valid_ccc(codes)
    return ",".join(codes)


def _assert_valid_ccc(codes: list[str]) -> None:
    """CCC 號列必須是 11 位數字。

    擋掉 config 裡打錯字的情況 —— 在下載前就發現，比下載完才發現便宜太多。
    """
    bad = [c for c in codes if not (c.isdigit() and len(c) == 11)]
    if bad:
        raise ValueError(
            f"config/hs_codes.yaml 的 code_query 必須是 11 位數字，不合格：{bad}"
        )


def regulated_countries() -> list[str]:
    """回傳受法規管制、進口量天生被壓抑的來源國。

    目前是 MP1（大陸物品有條件准許輸入）：中國大陸僅開放乾狗糧（牛肉口味）。
    這些國家的低進口量是法規造成的，不是市場偏好 —— 建模與解讀都要區隔，
    否則會把「法規不讓進」誤讀成「消費者不愛」。
    """
    return load("params").get("regulatory", {}).get("mp1_restricted_countries", [])
