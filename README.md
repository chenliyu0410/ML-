# 🐾 台灣寵物食品進口分析與需求預測

> 以海關月度進出口資料為基礎，驗證「寵物食品精緻化」假設，並建立來源國 × 品項的進口需求預測與採購建議模型。

![Python](https://img.shields.io/badge/python-3.10+-blue)
![Status](https://img.shields.io/badge/status-WIP-orange)
![License](https://img.shields.io/badge/license-MIT-green)

---

## 📌 專案動機

初步觀察顯示，台灣寵物食品的**進口總金額逐年上升，但進口總重量逐年下降**。

若此現象為真，代表單位重量價格（USD/kg）持續攀升 —— 市場正朝**高單價、精緻化**方向移動。

但單價上升有多個競爭性解釋，**本專案的第一項任務就是排除這些干擾，確認精緻化是否真實存在**：

| 競爭解釋 | 排除方式 |
|---|---|
| 通貨膨脹 | 以進口物價指數（IPI）/ CPI 平減，改看**實質單價** |
| 匯率變動 | 同時以 USD 與 TWD 計價交叉驗證 |
| 國際運費、原物料上漲 | 對照玉米、雞肉、SCFI 運價指數走勢 |
| 稅則號別改編 | 檢查 HS 版本切換年度（2017 / 2022）是否造成斷點 |
| **整體物價普遍上漲** | 對照「一般食品類」進口單價指數，比較**相對漲幅** |

> 🔑 唯有寵物食品的實質單價漲幅**顯著高於**整體食品，「精緻化」的結論才成立。

---

## 🎯 專案目標

| # | 目標 | 產出 |
|---|---|---|
| **1** | 驗證精緻化假設 | 實質單價指數趨勢圖 + 對照組比較 |
| **2** | 預測未來 12–24 個月進口需求 | 各國 × 品項的量 / 值 / 單價預測 |
| **3** | 產出採購建議名單 | 「高單價高成長」象限的國家 × 品項清單 |
| **4** | 找出成長驅動因子 | 特徵重要度排序（可解釋性產出） |

**範圍界定**：本階段**只做進口、只做寵物食品**。
出口機會分析與動物用藥需求列為 Phase 2，不在此 repo 的第一版範圍內。

---

## 📊 資料來源

### 主資料（必要）

| 來源 | 內容 | 取得方式 |
|---|---|---|
| **關港貿單一窗口－海關進出口統計** | 月度 × 稅則號別 × 國家別的量、值 | [綜合查詢](https://portal.sw.nat.gov.tw/APGA/GA30)，支援「按月」、「指定貨品號列」、「生產國家別」 |
| **關務署稅則稅率查詢** | 確認 HS / CCC 號列定義 | [web.customs.gov.tw](https://web.customs.gov.tw) |

> ⚠️ 網頁查詢有單次筆數上限，需分批下載後合併。若需完整 raw data，可洽關務署統計室購買。

### 輔助資料（用於排除干擾 / 加特徵）

| 來源 | 用途 |
|---|---|
| 主計總處 CPI、進口物價指數 IPI | 價格平減 |
| 中央銀行 USD/TWD 月均匯率 | 匯率效果剝離 |
| UN Comtrade | 國際市場對照（Phase 2 出口分析用） |
| SCFI / BDI 運價指數 | 運費成本控制變數 |
| 農業部動植物防疫檢疫署 輸入許可 | 品項合法性與新進品牌訊號（選配） |

---

## 🔢 稅則號別（HS Code）—— ⚠️ 這是全專案最容易做錯的一步

**寵物食品沒有單一稅號可以一次抓完。** 號列選錯，後面所有分析全部作廢。

### 建議起手範圍

| HS 6 碼 | 品名 | 備註 |
|---|---|---|
| `2309.10` | 犬或貓食品，零售包裝 | **核心稅號**，主戰場 |
| `2309.90` | 其他動物飼料調製品 | 含部分散裝寵物飼料，需人工判讀分項 |

### 需自行查證後決定是否納入

| 可能品項 | 可能落在 | 狀態 |
|---|---|---|
| 寵物肉乾 / 潔牙骨 | `1602` 調製肉類 或 `2309.10` | ❓ 待查 |
| 寵物保健品 / 營養補充 | `2106` 食品調製品 或 `3004` | ❓ 待查 |
| 貓砂（礦砂 / 豆腐砂 / 水晶砂） | `2508` / `3824` / 其他 | ❓ 待查，非食品，可能排除 |

### 執行步驟

1. 上關務署「稅則稅率查詢」，以**關鍵字**（狗、貓、寵物、飼料、pet）反查所有相關 CCC 號列
2. 台灣使用 **11 碼 CCC 號列**（HS 6 碼 + 稅則 2 碼 + 統計 2 碼 + 檢查碼 1 碼），下載時要決定分析粒度
3. 將最終決定的稅號清單與**納入/排除理由**寫進 `config/hs_codes.yaml`
4. ⚠️ 檢查 HS 版本改版年度是否造成號列斷點，必要時建立新舊號列對照表

> 💡 **這一步就是本專案的護城河。** 模型誰都能跑，但「知道 2309.90 裡哪些分項才算寵物食品」需要領域知識 —— 把判斷理由完整記錄在 config 裡，它比模型更有價值。

---

## 🗂️ 專案結構

```
pet-import-forecast/
├── README.md
├── requirements.txt
├── .gitignore                    # data/raw/ 不進版控
│
├── config/
│   ├── hs_codes.yaml             # ★ 稅號清單 + 納入/排除理由
│   └── params.yaml               # 模型超參數、預測期數
│
├── data/
│   ├── raw/                      # 原始下載檔（不進 git）
│   ├── interim/                   # 合併、清理後
│   └── processed/                 # 建模用 panel 資料
│
├── notebooks/
│   ├── 01_eda.ipynb              # 探索性分析、缺失值、離群值
│   ├── 02_price_validation.ipynb # ★ 精緻化假設驗證（平減 + 對照組）
│   ├── 03_features.ipynb         # 特徵工程實驗
│   ├── 04_baseline.ipynb         # Naive / SARIMA / Prophet
│   ├── 05_ml_forecast.ipynb      # LightGBM 全域模型
│   └── 06_clustering.ipynb       # 國家 × 品項分群
│
├── src/
│   ├── data/
│   │   ├── fetch_customs.py      # 下載 / 解析海關資料
│   │   └── clean.py              # 單位統一、缺失補值、國名標準化
│   ├── features/
│   │   └── build_features.py     # lag / rolling / 季節 / 外部變數
│   ├── models/
│   │   ├── train.py
│   │   ├── predict.py
│   │   └── evaluate.py           # 統一評估函式（含 baseline 比較）
│   └── viz/
│       └── plots.py
│
├── models/                        # 訓練好的模型檔（.pkl / .joblib）
├── reports/
│   └── figures/
└── tests/
```

---

## 📐 資料規格（processed panel）

建模用的最終資料應為**長格式 panel**：

| 欄位 | 型態 | 說明 |
|---|---|---|
| `ym` | date | 年月（YYYY-MM），主時間鍵 |
| `hs_code` | str | 稅則號別 |
| `country` | str | 生產國家（進口）|
| `value_usd` | float | 進口值 |
| `weight_kg` | float | 進口重量 |
| `unit_price` | float | `value_usd / weight_kg` ← **核心衍生欄位** |
| `unit_price_real` | float | 經 IPI 平減後的**實質單價** |

**唯一鍵**：`(ym, hs_code, country)`

> 🔑 **為什麼一定要用月資料**：年度資料從 2015 年起只有約 10 個點，任何 ML 模型都無法訓練。
> 改為 `月 × 稅號 × 國家` 的 panel 後，樣本數可從 10 筆放大到數萬筆，樹模型才有東西可學。

### 清理注意事項

- **國名標準化**：中國大陸 / 中國 / CHINA、美國 / USA 等寫法不一致，需建對照表
- **零值 vs 缺失**：某月某國沒有進口 → 應補 0 而非 NaN（會影響 lag 特徵）
- **稀疏序列處理**：交易月數 < 24 個月的國家 × 品項組合，建議先剔除或併入「其他」
- **離群值**：單筆超大金額可能是轉口或報關異常，用 IQR 檢查但**不要輕易刪除**，先查原因

---

## 🛠️ 特徵工程清單

| 類別 | 特徵 |
|---|---|
| **落後項 Lag** | `lag_1, lag_2, lag_3, lag_6, lag_12`（量、值、單價各一組） |
| **滾動統計** | `rolling_mean / std`（窗口 3, 6, 12）→ 捕捉趨勢與波動度 |
| **成長率** | MoM、YoY、12 個月 CAGR |
| **季節性** | `month`、`quarter`、月份的 `sin/cos` 週期編碼 |
| **市場結構** | 該國市占率 `share`、市占變化、HHI 集中度指數 |
| **類別編碼** | `country` 用 Target Encoding 或 LightGBM 原生 categorical |
| **外部變數** | USD/TWD 匯率、CPI、玉米/雞肉價格、SCFI 運價 |
| **事件 dummy** | COVID 期間、貿易協定生效、稅則改版年度 |

> ⚠️ **防資料洩漏**：所有 lag 與 rolling 特徵**只能用 t 時點以前的資料**。
> 標準化、Target Encoding 一律封裝進 `sklearn.Pipeline`，且只用訓練集擬合參數。

---

## 🤖 建模策略

### 三層遞進

```
① Baseline（一定要做，用來當比較基準）
   ├─ Naive：預測值 = 上期值
   └─ Seasonal Naive：預測值 = 去年同月值   ← 有季節性時很難打敗

② 統計時間序列
   ├─ SARIMA
   └─ Prophet                              ← 可解釋趨勢與季節分量

③ 機器學習（主力）
   └─ LightGBM / XGBoost 全域模型
      把所有國家 × 品項的序列疊在一起訓練一個模型，
      用 country / hs_code 當特徵區分 → 資料量放大，稀疏序列也能學
```

> 🔑 **Baseline 不是形式**：實務上很多時間序列專案的複雜模型打不贏 Seasonal Naive。
> 若 LightGBM 沒有明顯優於 baseline，那個結論本身就要誠實寫進報告。

### 分群模組（回答「該進口哪一國、哪一類」）

```
每個「國家 × 品項」組合 →
特徵向量 [單價水位, 單價 CAGR, 進口量 CAGR, 市占率, 市占變化, 波動度, 集中度]
        ↓ 標準化（K-Means 靠距離，必須做）
        ↓ PCA 降維
        ↓ K-Means（手肘法定 K + 輪廓係數驗證）
        ↓
   高單價高成長 ← 採購建議名單
   高單價停滯 / 低價走量 / 衰退
```

---

## 📏 評估與驗證

### 驗證策略

⚠️ **時間序列絕對不能用 `train_test_split` 隨機切分** —— 那等於用未來預測過去。

```
使用 TimeSeriesSplit（滾動原點回測）：

第 1 折  [====train====][val]
第 2 折  [======train======][val]
第 3 折  [========train========][val]
                                  ...

最後 12 個月完全保留為 holdout，全程不碰，最終只評估一次
```

### 指標

| 任務 | 指標 |
|---|---|
| 預測（迴歸） | MAE、RMSE、MAPE / sMAPE、**相對 baseline 的改善率** |
| 分群 | 輪廓係數（越接近 1 越好）、DB 指數（越小越好）、**+ 商業可解釋性人工判斷** |
| 分類（選配） | Precision / Recall / F1 / AUC |

> 💡 MAPE 在實際值接近 0 時會爆炸，稀疏序列建議改用 sMAPE 或 MASE。

---

## 🚧 開發路線圖

### Phase 0 — 資料底層（最耗時，別低估）
- [ ] 查證並敲定稅則號別清單，寫入 `config/hs_codes.yaml`
- [ ] 下載 2015-01 ~ 最新月的月度資料（稅號 × 國家）
- [ ] 國名標準化、單位統一、零值補齊
- [ ] 產出 processed panel，通過資料品質檢查

### Phase 1 — 假設驗證 ⭐ 專案價值最高的一段
- [ ] 計算名目 / 實質單價指數
- [ ] 建立對照組（一般食品類進口單價）
- [ ] 逐一排除通膨、匯率、運費、稅則改版
- [ ] **產出結論：精緻化假設成立或不成立**

### Phase 2 — 預測建模
- [ ] 建立 Naive / Seasonal Naive baseline
- [ ] SARIMA / Prophet 統計模型
- [ ] 特徵工程 pipeline
- [ ] LightGBM 全域模型 + 超參數調校
- [ ] 滾動回測 + holdout 最終評估
- [ ] 特徵重要度分析

### Phase 3 — 分群與建議
- [ ] 國家 × 品項特徵矩陣
- [ ] PCA + K-Means，用輪廓係數選 K
- [ ] 象限圖與採購建議名單

### Phase 4 — 產出
- [ ] 視覺化儀表板（Streamlit / Plotly Dash）
- [ ] 最終報告
- [ ] 資料更新腳本（每月自動重跑）

---

## ⚠️ 已知風險與陷阱

| 風險 | 說明 | 因應 |
|---|---|---|
| **稅號選錯** | 整份分析報廢 | Phase 0 花時間查證，理由寫進 config |
| **HS 版本斷點** | 2017 / 2022 改版造成序列不連續 | 建新舊對照表，或分段分析 |
| **資料洩漏** | 隨機切分、用未來資訊算特徵 | TimeSeriesSplit + Pipeline 封裝 |
| **樣本稀疏** | 小國家單一品項只有零星幾筆 | 設最低交易月數門檻，或併為「其他」 |
| **資訊保護遮罩** | 關務署對可能揭露個別廠商的資料做保護處理 | 檢查是否有異常空值或合併項 |
| **打不贏 baseline** | 複雜模型未必更好 | 誠實呈現，這本身是有效結論 |
| **範圍蔓延** | 想同時做出口、動物用藥 | 嚴守本階段只做進口食品 |

---

## 🚀 快速開始

```bash
git clone <repo-url>
cd pet-import-forecast

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 依序執行
python -m src.data.fetch_customs
python -m src.data.clean
python -m src.features.build_features
python -m src.models.train
```

### requirements.txt（起手）

```
pandas>=2.0
numpy
scikit-learn>=1.3
lightgbm
statsmodels
prophet
matplotlib
seaborn
plotly
pyyaml
jupyter
```

---

## 📁 .gitignore 重點

```gitignore
data/raw/
data/interim/
*.csv
*.xlsx
models/*.pkl
venv/
.ipynb_checkpoints/
__pycache__/
.env
```

> 原始資料不進版控：檔案大、且來源有使用條款。改為在 README 記錄取得方式，讓他人可自行重建。

---

## 🔮 Phase 2 展望（本 repo 暫不實作）

- **出口機會分析**：以 UN Comtrade 鏡像資料建立「國家 × 品項」矩陣，用協同過濾 / SVD 推薦台灣尚未出口但目標市場偏好的品項
- **動物用藥需求**：資料結構差異大（受管制、有許可證制度、樣本稀疏），需獨立設計

---

## 📄 License

MIT
