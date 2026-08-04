"""下載 / 解析海關進出口統計。

資料來源：關港貿單一窗口－綜合查詢
https://portal.sw.nat.gov.tw/APGA/GA30

查詢條件：按月 × 指定貨品號列 × 生產國家別

注意：網頁查詢有單次筆數上限，需分批下載後合併。
若需完整 raw data，可洽關務署統計室購買。
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from src import config


def fetch(hs_codes: list[str], start_ym: str, end_ym: str | None) -> pd.DataFrame:
    """依稅號與期間取得月度資料。

    TODO: 單一窗口沒有公開 API，實作上二選一：
      (a) 手動分批下載到 data/raw/，本函式只負責讀檔與合併
      (b) 用 requests + 解析查詢表單自動化（需處理筆數上限與分頁）
    先做 (a) 把 Phase 0 跑通，不要一開始就卡在爬蟲。
    """
    raise NotImplementedError


def load_raw(raw_dir: Path) -> pd.DataFrame:
    """讀取 data/raw/ 底下所有下載檔並合併成單一 DataFrame。

    TODO: 處理分批下載造成的重複列（同月同稅號同國家）。
    合併後應驗證 (ym, hs_code, country) 是否唯一。
    """
    raise NotImplementedError


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="params")
    args = parser.parse_args()

    cfg = config.load(args.config)
    codes = config.included_hs_codes()
    if not codes:
        raise SystemExit(
            "config/hs_codes.yaml 裡沒有任何 status: confirmed 的號列。\n"
            "請先完成 Phase 0 的稅號查證再執行本步驟。"
        )

    df = fetch(codes, cfg["data"]["start_ym"], cfg["data"]["end_ym"])
    out = config.resolve(cfg["paths"]["raw"]) / "customs_raw.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out)
    print(f"已寫入 {out}（{len(df):,} 列）")


if __name__ == "__main__":
    main()
