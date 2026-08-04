"""解析人工下載的海關 CSV，批次合併成 panel。

╔═══════════════════════════════════════════════════════════════════╗
║ 為什麼沒有爬蟲                                                     ║
║                                                                   ║
║ 關港貿單一窗口（GA30）與國際貿易署貿易統計網（FSC3000C）           ║
║ 兩個系統都有驗證碼，已實測確認無法自動化。                          ║
║                                                                   ║
║ 因此本專案的資料流是：                                             ║
║   人工依 docs/download_sop.md 下載 → data/raw/import_YYYY.csv      ║
║   → 本模組解析合併 → clean.py 清理 → processed panel                ║
╚═══════════════════════════════════════════════════════════════════╝

用法：
    python -m src.data.parse_downloads              # 解析合併
    python -m src.data.parse_downloads --reconcile  # 合併後與管道 B 對帳
"""

from __future__ import annotations

import argparse
import warnings
from pathlib import Path

import pandas as pd

from src import config


class TruncationError(RuntimeError):
    """下載檔疑似被筆數上限截斷。"""


def read_with_fallback(path: Path, encodings: list[str]) -> pd.DataFrame:
    """依序嘗試多種編碼讀檔。

    政府網站匯出的 CSV 編碼不統一，utf-8-sig / cp950 / big5 都遇得到。
    硬編一種編碼，換一批檔案就爆。
    """
    last_error: Exception | None = None
    for enc in encodings:
        try:
            return pd.read_csv(path, encoding=enc)
        except (UnicodeDecodeError, LookupError) as exc:
            last_error = exc
            continue
    raise ValueError(
        f"無法解析 {path.name}，試過的編碼：{encodings}。\n"
        f"最後錯誤：{last_error}\n"
        f"請確認實際編碼並補進 config/params.yaml 的 ingest.encoding_candidates。"
    )


def discover_files(raw_dir: Path, pattern: str) -> list[Path]:
    """掃描 data/raw/ 底下符合命名規則的下載檔。

    檔名不照 SOP 命名就會被漏掉，所以掃不到檔要明確報錯，
    不能安靜回傳空 list 讓後面拿到空 DataFrame。
    """
    files = sorted(raw_dir.glob(pattern))
    if not files:
        raise FileNotFoundError(
            f"{raw_dir} 底下找不到符合 {pattern} 的檔案。\n"
            f"請依 docs/download_sop.md 人工下載，檔名須為 import_YYYY.csv。"
        )
    return files


def check_truncation(
    df: pd.DataFrame,
    path: Path,
    suspect_limits: tuple[int, ...] = (10000, 50000, 65536),
) -> None:
    """偵測筆數是否剛好卡在常見的查詢上限。

    被截斷的下載檔看起來完全正常 —— 沒有錯誤訊息，只是資料少了一截。
    筆數剛好等於整數上限就是最明顯的訊號，值得停下來確認。
    """
    n = len(df)
    if n in suspect_limits:
        raise TruncationError(
            f"{path.name} 筆數剛好等於 {n}，疑似被查詢上限截斷。\n"
            f"請把該年度改成分半年或分季下載後重試。"
        )


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """把下載檔的中文欄名對應到 panel 標準欄名。

    目標欄名：ym, hs_code, country, value_usd, value_twd, weight_kg,
             reimport_value_usd

    TODO: 實際欄名要等第一份下載檔到手才知道（單一窗口的表頭會隨勾選的
    統計值變動）。拿到檔案後在此建立對照，且**未對應到的欄位要 warn**，
    不要靜默丟掉 —— 丟掉的可能正好是復進口欄。
    """
    raise NotImplementedError("待第一份下載檔到手後補上欄名對照")


def validate_panel(df: pd.DataFrame, keys: list[str]) -> None:
    """驗證 panel 唯一鍵。

    分批下載很容易在年度邊界重複（例如 2016 那批含了 2017-01）。
    重複列會讓同月同國同稅號的金額被灌水，且不會有任何錯誤訊息。
    """
    dup = df.duplicated(subset=keys, keep=False)
    if dup.any():
        sample = df.loc[dup, keys].head(10)
        raise ValueError(
            f"panel 唯一鍵 {keys} 有 {int(dup.sum())} 列重複。\n"
            f"多半是分批下載的期間重疊。前 10 列：\n{sample}"
        )


def parse_all(cfg: dict) -> pd.DataFrame:
    """讀取所有下載檔，合併成單一 DataFrame。"""
    raw_dir = config.resolve(cfg["paths"]["raw"])
    ingest = cfg["ingest"]

    frames = []
    for path in discover_files(raw_dir, ingest["raw_pattern"]):
        df = read_with_fallback(path, ingest["encoding_candidates"])
        check_truncation(df, path)
        df["_source_file"] = path.name       # 保留來源，出問題才追得回去
        frames.append(df)
        print(f"  讀入 {path.name}：{len(df):,} 列")

    merged = pd.concat(frames, ignore_index=True)
    merged = normalize_columns(merged)
    validate_panel(merged, cfg["data"]["panel_keys"])
    return merged


def reconcile_unit_price(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """與管道 B 官方「平均單價(重量)」對帳 —— Phase 0 的品質關卡。

    管道 B 已經算好 USD/kg。拿它跟自己算的 value_usd / weight_kg 比，
    對不起來就代表口徑錯了。依機率排序的常見原因：
      1. 復進口沒扣除（管道 A 下載的是「含復進口」）
      2. 幣別搞混（USD vs TWD）
      3. 重量單位搞混（公噸 vs 公斤，差 1000 倍）
      4. 稅號範圍不一致（對帳時漏抓 4205）

    這個對帳只要做一次，卻能擋掉整份分析最致命的錯誤。

    TODO: 管道 B 只輸出 XLS，需 pd.read_excel。欄名同樣待實檔確認。
    """
    raise NotImplementedError("待管道 B 對帳檔到手後補上")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="params")
    parser.add_argument(
        "--reconcile",
        action="store_true",
        help="合併後與管道 B 官方平均單價對帳（Phase 0 品質關卡，強烈建議跑）",
    )
    args = parser.parse_args()

    cfg = config.load(args.config)

    if not config.included_hs_codes():
        raise SystemExit(
            "config/hs_codes.yaml 裡沒有任何 status: confirmed 的號列。\n"
            "請先完成 Phase 0 的稅號查證再執行本步驟。"
        )
    print(f"預期涵蓋號列：{config.hs_query_string()}")

    df = parse_all(cfg)

    if args.reconcile:
        if not cfg["reconcile"]["enabled"]:
            warnings.warn("reconcile.enabled = false，跳過對帳（不建議）", stacklevel=2)
        else:
            df = reconcile_unit_price(df, cfg)
    else:
        warnings.warn(
            "未執行對帳。建議加上 --reconcile —— 口徑錯了要到很後面才會發現。",
            stacklevel=2,
        )

    out = config.resolve(cfg["paths"]["interim"]) / "customs_merged.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out)
    print(f"已寫入 {out}（{len(df):,} 列）")


if __name__ == "__main__":
    main()
