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


def included_hs_codes() -> list[str]:
    """回傳已確認納入的稅則號別。

    只回傳 status == "confirmed" 的號列。待查證（pending）的項目不會出現在
    這裡 —— 這是刻意的：號列沒查證完就開始建模，等於整份分析建在流沙上。
    """
    cfg = load("hs_codes")
    return [
        item["code"]
        for item in cfg.get("include", [])
        if item.get("status") == "confirmed"
    ]
