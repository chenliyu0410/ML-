"""訓練：Baseline → 統計模型 → LightGBM 全域模型。

三層遞進，順序不可跳。先有 baseline 才知道後面的模型值不值得。

全域模型：把所有國家 × 品項的序列疊在一起訓練一個模型，用 country /
hs_code 當特徵區分。資料量放大，稀疏序列也能借用其他序列學到的模式。
"""

from __future__ import annotations

import argparse

from src import config


def make_cv(n_splits: int):
    """滾動原點回測。

    時間序列絕對不能用 train_test_split 隨機切分 —— 那等於用未來預測過去。
    """
    from sklearn.model_selection import TimeSeriesSplit

    return TimeSeriesSplit(n_splits=n_splits)


def split_holdout(df, months: int):
    """切出最後 N 個月做 holdout：全程不碰，最終只評估一次。

    TODO: 依 ym 切，不是依列數切。panel 每個月有多列。
    """
    raise NotImplementedError


def train_baseline(df, cfg):
    """Naive 與 Seasonal Naive。先做這個。"""
    raise NotImplementedError


def train_lightgbm(X_train, y_train, X_val, y_val, params: dict):
    """LightGBM 全域模型。

    TODO: country / hs_code 用 LightGBM 原生 categorical，
    不要先做 one-hot（維度爆炸且樹分裂效率變差）。
    """
    raise NotImplementedError


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="params")
    parser.add_argument(
        "--stage",
        choices=["baseline", "stats", "ml", "all"],
        default="all",
        help="baseline 一定要先跑過，後面的模型才有比較基準",
    )
    args = parser.parse_args()

    cfg = config.load(args.config)
    print(f"holdout: 最後 {cfg['split']['holdout_months']} 個月")
    raise NotImplementedError


if __name__ == "__main__":
    main()
