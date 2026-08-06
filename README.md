# 🐾 台灣寵物食品進口需求預測

> **精緻化已確認成立。** 本專案在這個前提上，用 `月 × 稅號 × 國家` 的 panel 資料建立
> 進口需求預測模型（全域 LightGBM）與採購建議分群（PCA + K-Means）。

![Python](https://img.shields.io/badge/python-3.10+-blue)
![Status](https://img.shields.io/badge/status-WIP-orange)
![License](https://img.shields.io/badge/license-MIT-green)

---

## ✅ 已確認的前提：精緻化確實發生

台灣寵物食品**進口總金額逐年上升、進口總重量逐年下降**，單位重量價格（USD/kg）持續攀升 ——
市場正朝**高單價、精緻化**方向移動。

這個結論已排除下列競爭性解釋：

| 競爭解釋 | 排除方式 | 狀態 |
|---|---|---|
| 通貨膨脹 | 以進口物價指數（IPI）平減，改看**實質單價** | ✅ 已排除 |
| 匯率變動 | 同時以 USD 與 TWD 計價交叉驗證 | ✅ 已排除 |
| 國際運費、原物料上漲 | 對照玉米、雞肉、SCFI 運價指數走勢 | ✅ 已排除 |
| 稅則號別改編 | 檢查 HS 版本切換年度（2017 / 2022）無斷點 | ✅ 已排除 |
| 整體物價普遍上漲 | 對照「一般食品類」進口單價指數，寵物食品實質漲幅**顯著較高** | ✅ 已排除 |

> 📝 **待補**：上表的實際數字（實質單價 CAGR、對照組相對漲幅、驗證期間）請填入
> `reports/premiumization_evidence.md`，並在 `notebooks/02_price_validation.ipynb` 留下可重跑的證據。
> 前提本身已定論，但 repo 目前還沒有讓別人重建這個結論的紀錄。

### 🔑 這個前提如何改變建模決策

精緻化成立不只是一個結論，它直接決定了三件建模上的事：

| 影響 | 說明 |
|---|---|
| **目標變數有趨勢** | 單價是趨勢序列 → **樹模型無法外推**，直接預測水位會系統性低估。見 [目標變數設計](#-目標變數設計--本專案最關鍵的-ml-決策) |
| **量價必須分開建模** | 「值上升、量下降」代表量與價由不同機制驅動，把 `value_usd` 當單一目標會把兩個相反的訊號混在一起 |
| **高單價品類不能漏** | `4205` 寵物零食是精緻化程度最高的品類，漏抓會讓目標變數本身偏誤 |

---

## 🎯 ML 問題定義

### 兩個任務

| # | 任務 | ML 類型 | 產出 |
|---|---|---|---|
| **1** | 預測未來 12–24 個月各國 × 品項的進口量與單價 | 監督式回歸（多序列 / 全域模型） | 量 / 價 / 值 的預測區間 |
| **2** | 找出「高單價高成長」的來源國 × 品項 | 非監督分群 | 採購建議名單 |
| **3** | 找出成長驅動因子 | 可解釋性分析 | 特徵重要度 + SHAP |

### 資料形狀

| 項目 | 設定 |
|---|---|
| 觀測單位 | 一個 `(ym, hs_code, country)` = 一列 |
| 實體（序列）鍵 | `(hs_code, country)` —— 一個「國家 × 品項」就是一條獨立時間序列 |
| 時間鍵 | `ym`（月），2016-01 起 |
| 序列數量 | 約 2 稅號 × 數十個實際有交易的國家 |
| 樣本數 | 數千至數萬列 |
| 預測期 | 12 個月（目標 12–24） |

> 🔑 **為什麼一定要用月資料**：年度資料從 2016 年起只有約 10 個點，任何 ML 模型都無法訓練。
> 改為 `月 × 稅號 × 國家` 的 panel 後，樣本數從 10 筆放大到數萬筆，樹模型才有東西可學。

### 為什麼用全域模型（global model）而非每條序列各訓一個

```
逐序列模型（local）                    全域模型（global）
每個國家 × 品項訓一個 SARIMA     →     所有序列疊成一張表訓一個 LightGBM
├─ 小國只有零星幾筆 → 訓不動             ├─ country / hs_code 當特徵區分序列
├─ 數十個模型要各自調參維護              ├─ 稀疏序列可借用其他序列學到的季節與趨勢模式
└─ 序列間的共同模式學不到                └─ 一個模型、一套 pipeline
```

代價是全域模型假設序列間有可共享的結構。若某條序列行為特殊（例：受 MP1 管制的中國大陸），
需要靠特徵告訴模型，而不是期待它自己發現。

---

## 🧮 目標變數設計 —— 本專案最關鍵的 ML 決策

這一節是精緻化前提落到 ML 上最直接的後果，做錯的話後面所有指標都是假的。

### ⚠️ 問題一：樹模型不能外推

LightGBM 的預測值是**葉節點裡訓練樣本的統計量**，數值上被訓練集的值域夾住。
單價既然持續上升，holdout 期的真實單價會落在訓練集**沒見過的高檔區間** ——
模型只能輸出它見過的最高值，而且預測期愈往後、低估愈嚴重。

**這是趨勢序列 + 樹模型的結構性缺陷，不是調參能解決的。**

三種解法，建議 A：

| 解法 | 做法 | 取捨 |
|---|---|---|
| **A. 差分目標** ⭐ | 目標改成 `log(y_t) - log(y_{t-12})`，趨勢被差分掉變成定態問題，預測完再累加回去 | 首選。同時處理趨勢與異質變異數 |
| **B. Detrend + 殘差** | 先用線性回歸/HP 濾波抽掉趨勢，樹模型只學殘差 | 趨勢外插的假設要另外交代 |
| **C. 混合模型** | 線性模型抓趨勢，LightGBM 抓非線性殘差 | 最有彈性，但要維護兩個模型 |

> 🔬 **診斷方式**：畫 holdout 的**殘差對時間**圖。若殘差隨時間單調上升 → 就是外推失敗，
> 不是模型不夠複雜。這張圖比任何單一 MAE 數字都能說明問題。

### ⚠️ 問題二：三個目標的恆等式一致性

`unit_price ≡ value_usd / weight_kg`。三個各自獨立預測，結果會自相矛盾
（預測的量 × 預測的價 ≠ 預測的值）。

**只預測兩個，第三個用恆等式導出**：

```
預測 weight_kg（量）  ─┐
                       ├─→ value_usd = weight_kg × unit_price（導出）
預測 unit_price（價） ─┘
```

選這兩個當直接目標，是因為精緻化的核心命題就是**量價分離** ——
把量與價分開建模，才能回答「成長來自買更多還是買更貴」。

### ⚠️ 問題三：實質 vs 名目

**訓練用實質單價（IPI 平減）**，否則模型會把通膨學成需求訊號。
要輸出名目值時，再把通膨路徑乘回去，並在報告中明講這一步用了什麼通膨假設。

### ⚠️ 問題四：零膨脹與間歇性需求

補 0 的月份很多（小國某些月份沒有進口），目標分布在 0 有一個尖峰。
`objective: regression_l1`（目前 `params.yaml` 的設定）會把預測往 0 拉。

| 選項 | 適用 |
|---|---|
| `objective: tweedie` | 零膨脹的連續正值，一步到位 |
| 二階段模型 | 先分類「當月有無進口」，再對非零樣本回歸量 |
| 提高 `min_active_months` 門檻 | 直接把太稀疏的序列併入「其他」（現設 24 個月） |

---

## 🛠️ 特徵工程

實作見 [`src/features/build_features.py`](src/features/build_features.py)，參數見 `config/params.yaml` 的 `features` 區塊。

| 類別 | 特徵 | 為什麼 |
|---|---|---|
| **落後項 Lag** | `lag_1, 2, 3, 6, 12`（量、值、單價各一組） | 時序自相關的主力訊號 |
| **滾動統計** | `rolling_mean / std`（窗口 3, 6, 12） | 趨勢與**波動度**，std 是穩定性訊號 |
| **成長率** | MoM、YoY、12 個月 CAGR | 讓模型直接看到變化率而非水位 |
| **季節性** | `month`、`quarter`、月份 `sin/cos` 週期編碼 | 週期編碼讓 12 月與 1 月在特徵空間相鄰 |
| **市場結構** | 市占率 `share`、市占變化 `share_delta`、HHI 集中度 | 同月同稅號橫斷面資訊，捕捉競爭態勢 |
| **法規 flag** | `is_regulated_source`（MP1） | 告訴模型哪些序列受外生管制 |
| **類別編碼** | `country` / `hs_code` 用 LightGBM **原生 categorical** | 不要先 one-hot：維度爆炸且樹分裂效率變差 |
| **外部變數** | USD/TWD 匯率、CPI、玉米/雞肉價格、SCFI 運價 | 成本面控制變數 |
| **事件 dummy** | COVID 期間、貿易協定生效、稅則改版年度 | 結構斷點 |

### 🚨 防資料洩漏的三條鐵律

`build_features.py` 的每個函式都遵守這三條，改動時不要破壞：

```
1. 一律先 groupby(hs_code, country) 再 shift
   → 不同國家的序列不可互相污染

2. rolling 之前先 shift(1)
   → 否則時點 t 的 rolling_mean 含 t 自己，等於把答案餵給模型

3. 標準化與 Target Encoding 不在特徵層做
   → 一律封裝進 sklearn.Pipeline，只用訓練集擬合參數
```

> ⚠️ **外部變數有發布時滯**：某月的 CPI 通常下個月才公布。用當月值等於假設
> 「預測當下已知當月 CPI」，實務上不成立 → 一律 `shift(1)` 或改用預測值，並在報告中揭露這個假設。
> （`add_external()` 目前還是 `NotImplementedError`，實作時記得處理。）

---

## 🤖 建模策略

### 三層遞進（順序不可跳）

```
① Baseline —— 一定要先做，用來當比較基準
   ├─ Naive：預測值 = 上期值
   └─ Seasonal Naive：預測值 = 去年同月值   ← 有季節性時很難打敗

② 統計時間序列
   ├─ SARIMA (1,1,1)(1,1,1,12)
   └─ Prophet                              ← 可拆解趨勢與季節分量，且能外推趨勢

③ 機器學習（主力）
   └─ LightGBM 全域模型
      objective: regression_l1（考慮改 tweedie）
      country / hs_code 用原生 categorical
      early_stopping_rounds: 100
```

> 🔑 **Baseline 不是形式**：實務上很多時間序列專案的複雜模型打不贏 Seasonal Naive。
> 若 LightGBM 沒有明顯優於 baseline，那個結論本身就要誠實寫進報告 —— 比硬凹一個好看的數字有價值。
>
> 💡 順帶一提：Prophet 在這裡有個 LightGBM 沒有的優勢 —— **它能外推趨勢**。
> 精緻化前提下，Prophet 可能在長 horizon 上表現意外地好，這件事值得驗證而不是假設。

### 多步預測：遞迴 vs 直接

預測 12 個月有兩種做法，這是很容易做錯的一步：

| 策略 | 做法 | 問題 |
|---|---|---|
| **遞迴 recursive** | 用 h=1 的預測值當 h=2 的 `lag_1` | 誤差逐期累積；h=12 時 `lag_1..lag_11` 全是預測值 |
| **直接 direct** ⭐ | 每個 horizon 各訓一個模型，或把 `h` 當特徵 | 要維護多組模型，但誤差不累積 |

> 🚨 **最常見的錯誤**：訓練時用真實的 `lag_1`，推論時卻只有預測出來的 `lag_1` ——
> 訓練與推論的特徵分布不一致，離線指標會漂亮得不像真的。
>
> 採直接法時，horizon = h 的模型**只能用 `lag_h` 以上的特徵**。
> 例：h=12 的模型不可以用 `lag_1`，因為預測當下拿不到未來 11 個月的資料。

### 分群模組（回答「該進口哪一國、哪一類」）

```
每個「國家 × 品項」組合
  ↓ 彙總成特徵向量（固定彙總視窗，例：最近 36 個月）
    [單價水位, 單價 CAGR, 進口量 CAGR, 市占率, 市占變化, 波動度, HHI]
  ↓ 標準化 ← K-Means 靠歐氏距離，不做標準化等於讓量綱最大的特徵主導分群
  ↓ PCA（保留 90% 變異）
  ↓ K-Means（k_range 2–10，手肘法 + 輪廓係數雙重驗證）
  ↓
 高單價高成長 ← 採購建議名單
 高單價停滯 / 低價走量 / 衰退
```

| 注意事項 | 原因 |
|---|---|
| 標準化必做 | K-Means 距離對量綱敏感；`share`（0–1）與 `unit_price`（數十 USD）不能直接比 |
| 輪廓係數不能單看 | K 小的時候輪廓係數天然偏高 → 手肘法與輪廓係數都要看，再加商業可解釋性人工判斷 |
| 排除受管制來源 | `params.yaml → regulatory.exclude_from_clustering: true`，理由見下方護欄一節 |
| 固定彙總視窗 | 彙總視窗跟著資料更新而變動的話，分群結果無法跨期比較 |

---

## 📏 驗證與評估

### ⚠️ 時間序列絕對不能用 `train_test_split` 隨機切分

那等於用未來預測過去。

```
使用 TimeSeriesSplit（滾動原點回測），n_splits=5：

第 1 折  [====train====]<gap>[val]
第 2 折  [======train======]<gap>[val]
第 3 折  [========train========]<gap>[val]
                                        ...

最後 12 個月完全保留為 holdout，全程不碰，最終只評估一次
```

| 設定 | 值 | 為什麼 |
|---|---|---|
| `n_splits` | 5 | — |
| `gap` | `horizon - 1`（h=12 時為 11） | 模擬「預測當下看不到未來 11 個月」，否則長 horizon 的離線指標偏樂觀 |
| `holdout_months` | 12 | 全程不碰，最終只評估一次 |

> 🚨 **panel 的切分必須依 `ym` 切，不是依列數切**。每個月有數十列（多國多品項），
> 依列數切會把同一個月切開，train 與 val 混到同月資料。
> （`train.py → split_holdout()` 的 TODO 就是這件事。）

### 指標

| 任務 | 指標 |
|---|---|
| 預測（迴歸） | MAE、RMSE、sMAPE、**MASE**、相對 baseline 的改善率 |
| 分群 | 輪廓係數（越接近 1 越好）、DB 指數（越小越好）**+ 商業可解釋性人工判斷** |

實作見 [`src/models/evaluate.py`](src/models/evaluate.py)。

| 指標 | 讀法 |
|---|---|
| **MASE** ⭐ | **< 1 才代表打贏 seasonal naive**。「有沒有贏 baseline」直接寫在數值上，不用另算改善率 |
| **sMAPE** | MAPE 在實際值接近 0 時會爆炸；本專案有大量補 0 月份，一律用 sMAPE 取代 MAPE |
| **improvement_pct** | 相對 baseline 的改善率。這是報告裡最該被看見的數字，絕對誤差好不好看是其次 |

### 🚨 不要只看整體平均指標

幾個大國的量級會把整體 MAE 平均掉，小國就算預測得一塌糊塗也看不出來。**必須分層報告**：

| 分層維度 | 為什麼 |
|---|---|
| 稅號（`2309.10` vs `4205`） | 兩個品類的量級與行為差很多 |
| 序列規模（大國 / 中 / 小國） | 檢查模型是不是只在大國有效 |
| Horizon（h=1, 3, 6, 12） | 誤差隨 horizon 惡化的速度，比單一平均值有資訊量 |
| 加權方式 | 用 `value_usd` 加權的 MAE 更貼近商業意義；未加權的 MAE 會被一堆小序列主導 |

---

## 🔍 可解釋性（目標 3：找出成長驅動因子）

| 方法 | 注意事項 |
|---|---|
| LightGBM feature importance | 用 `importance_type='gain'`，不要用預設的 `'split'`（高基數特徵天生分裂次數多） |
| SHAP | 全域 summary plot + 單一序列的 force plot。可回答「這個國家的成長是誰貢獻的」 |
| Permutation importance | 高相關特徵（`lag_1` vs `roll_mean_3`）會**互相掩護、兩者都被低估** → 先看特徵相關矩陣再解讀 |

### 🚧 護欄：MP1 管制不是市場偏好

中國大陸僅開放「乾狗糧（牛肉口味）」一項（MP1 EX 註記），進口量天生受管制壓抑。

> 🚨 **特徵重要度若顯示 `country=中國大陸` 很重要，要先確認模型是在學管制，而不是在學消費者偏好。**
> 沒有這道護欄，分群會把受管制國家丟進「低價衰退」象限並建議「不值得採購」——
> 那個建議建立在錯誤的因果上。

這是只有領域知識才看得出來的事，也是本專案相對於「純跑模型」的優勢所在。
處理方式：`is_regulated_source` 當特徵給模型，分群時依 `exclude_from_clustering` 排除。

---

## 📊 資料

### 稅則號別（HS Code）—— 已確認，兩個都要抓

| CCC 號列 | 貨名 | 簽審 |
|---|---|---|
| **`2309.10.00.00-2`** | 供零售用之貓狗食品 | B01、MP1 |
| **`4205.00.90.10-4`** | 由動物皮製成供寵物嚼咬之製品（咬膠、潔牙骨、牛皮骨） | B01 |

> 🚨 **`4205` 歸在皮革章（第 42 章）而非食品章（第 23 章）。**
> 只抓 `2309.10` 的話，整個寵物零食品類會憑空消失 —— 而零食正是精緻化程度最高、單價最貴的品類，
> **漏掉會讓目標變數本身偏誤**，不只是少一個類別而已。

品類邊界依防檢署「犬貓寵物食品輸入檢疫條件」的官方定義。
完整清單、納入/排除理由與待查號列（`1602` 肉條、`2106`/`3004` 保健品、`2309.90` 散裝）
見 [`config/hs_codes.yaml`](config/hs_codes.yaml)。

> 💡 **這一步是本專案的護城河。** 模型誰都能跑，但「知道 2309.90 裡哪些分項才算寵物食品」
> 需要領域知識 —— 判斷理由完整記錄在 config 裡，它比模型更有價值。

### 資料取得：人工下載，不是爬蟲

**兩個官方查詢系統都有驗證碼（CAPTCHA），已實測確認無法寫爬蟲。**
所以本專案沒有 `fetch_customs.py`，取而代之的是一份 SOP ＋ 一支解析合併腳本。

| 管道 | 用途 |
|---|---|
| **A. 關港貿單一窗口 [GA30](https://portal.sw.nat.gov.tw/APGA/GA30)** | 主資料，可直接輸出 **CSV** |
| **B. 貿易統計網 [FSC3020F](https://publicinfo.trade.gov.tw/cuswebo/FSC3000C?table=FSC3020F)** | 對帳用，有內建「平均單價(重量)」官方報表 |
| C. 政府資料開放平臺 | ❌ 無貨品別與國家別，不適用 |

輔助資料：[匯率 FSC3070I](https://publicinfo.trade.gov.tw/cuswebo/FSC3000C?table=FSC3070I)（各月海關實際使用匯率，比央行牌價更貼合報關實務）、
主計總處 CPI / IPI、SCFI 運價指數。

完整下載設定與分批策略見 [`docs/download_sop.md`](docs/download_sop.md)，
每次下載的紀錄寫進 [`data/raw/MANIFEST.md`](data/raw/MANIFEST.md)。

### 🔒 品質關卡：與管道 B 官方單價對帳

用管道 B 的「平均單價(重量)」報表抓同一組稅號、同一期間的官方單價，
和自己用 `value_usd / weight_kg` 算的結果對照（容差 1%，對不起來就 `raise`）。

> 🔑 **兩者對不起來，代表口徑錯了。** 常見原因：復進口沒扣、幣別搞混（USD vs TWD）、
> 重量單位搞混（公噸 vs 公斤）、稅號範圍不一致（漏抓 4205）。
> 這個對帳只做一次，卻能擋掉整份分析最致命的錯誤。

> ⚠️ **復運（復進口 / 復出口）是很多人漏掉的陷阱**：國貨出口後退回也算進口。
> 分析「台灣市場對寵物食品的需求」必須扣除，否則會高估。

### processed panel 規格

| 欄位 | 型態 | 說明 |
|---|---|---|
| `ym` | date | 年月（YYYY-MM），主時間鍵 |
| `hs_code` | str | 稅則號別 |
| `country` | str | 生產國家 |
| `value_usd` | float | 進口值（由量價導出，非直接預測目標） |
| `weight_kg` | float | 進口重量 ← **直接預測目標** |
| `unit_price` | float | `value_usd / weight_kg` |
| `unit_price_real` | float | 經 IPI 平減後的**實質單價** ← **直接預測目標** |
| `is_regulated_source` | int | MP1 管制來源 flag |

**唯一鍵**：`(ym, hs_code, country)`

### 清理注意事項

| 項目 | 處理 | 對 ML 的影響 |
|---|---|---|
| 國名標準化 | 中國大陸/中國/CHINA、美國/USA 建對照表 | 不做的話同一國會被拆成多條序列 |
| 零值 vs 缺失 | 某月某國沒進口 → **補 0 而非 NaN** | NaN 會讓 lag 特徵斷裂 |
| 稀疏序列 | 交易月數 < 24 個月 → 併入「其他」或剔除 | 樣本太少的序列只會製造噪音 |
| 離群值 | IQR (k=3) **只標記不刪除** | 可能是轉口或報關異常，先查原因 |
| 資訊保護遮罩 | 關務署對可能揭露個別廠商的細項會遮罩 | 出現異常空白或合併值時先想到這個原因 |

---

## 🗂️ 專案結構

```
pet-import-forecast/
├── config/
│   ├── hs_codes.yaml             # ★ 稅號清單 + 納入/排除理由
│   ├── country_map.yaml          # 國名標準化對照表
│   └── params.yaml               # ★ 所有 magic number 集中在此
│
├── docs/download_sop.md          # 人工下載作業程序（有驗證碼，無法爬蟲）
│
├── data/
│   ├── raw/                      # 原始下載檔（不進 git）
│   │   └── MANIFEST.md           # ★ 下載紀錄，這份進版控
│   ├── interim/                  # 合併、清理後
│   └── processed/                # 建模用 panel
│
├── notebooks/
│   ├── 01_eda.ipynb              # 探索性分析、缺失值、離群值
│   ├── 02_price_validation.ipynb # 精緻化證據（結論已定，補可重跑紀錄）
│   ├── 03_features.ipynb         # ★ 特徵工程實驗 + 洩漏檢查
│   ├── 04_baseline.ipynb         # ★ Naive / Seasonal Naive / SARIMA / Prophet
│   ├── 05_ml_forecast.ipynb      # ★ LightGBM 全域模型 + SHAP
│   └── 06_clustering.ipynb       # ★ PCA + K-Means 分群
│
├── src/
│   ├── config.py
│   ├── data/
│   │   ├── parse_downloads.py    # 解析人工下載的 CSV/XLS，批次合併成 panel
│   │   └── clean.py              # 單位統一、缺失補值、國名標準化
│   ├── features/build_features.py # ★ lag / rolling / 季節 / 市場結構（防洩漏）
│   ├── models/
│   │   ├── train.py              # ★ baseline → stats → LightGBM
│   │   ├── predict.py
│   │   └── evaluate.py           # ★ 統一評估函式（含 MASE 與 baseline 比較）
│   └── viz/plots.py
│
├── models/                        # 訓練好的模型檔（.pkl / .joblib）
├── reports/figures/
└── tests/
```

---

## 🚧 開發路線圖

### ✅ Phase 1 — 精緻化驗證（結論已定）
- [x] ~~確認核心稅號~~ → `2309.10.00.00-2`、`4205.00.90.10-4`
- [x] ~~確認資料管道~~ → 兩個官方系統皆有驗證碼，改採人工下載
- [x] ~~驗證精緻化假設~~ → **成立**，五項競爭解釋均已排除
- [ ] 補上可重跑的證據紀錄（`reports/premiumization_evidence.md` + notebook 02）

### Phase 0 — 資料底層（ML 的前置，最耗時，別低估）
- [ ] 補查擴充號列（1602 肉條、2106/3004 保健品、2309.90 散裝）
- [ ] 完成 `config/hs_codes.yaml`（含納入/排除理由）
- [ ] 依 SOP 下載 2016-01 ~ 最新月，逐年存入 `data/raw/`
- [ ] `parse_downloads.py` 合併多年檔案
- [ ] 扣除復進口、國名標準化、單位統一、零值補齊
- [ ] **與管道 B 官方「平均單價」對帳** ← 品質關卡
- [ ] 產出 processed panel

### Phase 2 — 預測建模 ⭐ 現在的專案重心
- [ ] **決定目標變數變換**（log 差分 vs detrend vs 混合）← 先做這個，其他都建立在它上面
- [ ] 完成 `split_holdout()`：依 `ym` 切，不是依列數切
- [ ] Naive / Seasonal Naive baseline，算出 MASE 的分母尺度
- [ ] SARIMA / Prophet（順便驗證「Prophet 能外推趨勢」是否真的有優勢）
- [ ] 補完 `add_external()` 與 `add_event_dummies()`，含發布時滯 shift
- [ ] 特徵工程 pipeline + **洩漏檢查**（殘差對時間圖）
- [ ] LightGBM 全域模型（原生 categorical、tweedie vs L1 比較）+ 超參數調校
- [ ] 直接多步預測（每個 horizon 一組特徵集）
- [ ] 滾動回測（含 `gap`）+ holdout 最終評估
- [ ] **分層評估**（依稅號 / 序列規模 / horizon）
- [ ] 特徵重要度（gain）+ SHAP + MP1 護欄檢查

### Phase 3 — 分群與建議
- [ ] 國家 × 品項特徵矩陣（固定彙總視窗）
- [ ] 標準化 → PCA(0.90) → K-Means，手肘法 + 輪廓係數選 K
- [ ] 排除受管制來源
- [ ] 象限圖與採購建議名單

### Phase 4 — 產出
- [ ] 視覺化儀表板（Streamlit / Plotly Dash）
- [ ] 最終報告
- [ ] 資料更新腳本（季度人工下載 + 自動重跑）

---

## ⚠️ 已知風險與陷阱

### ML 風險

| 風險 | 說明 | 因應 |
|---|---|---|
| **樹模型無法外推趨勢** | 精緻化＝單價持續上升，LightGBM 會系統性低估且愈遠愈嚴重 | 目標改差分 / detrend / 混合模型；用殘差對時間圖診斷 |
| **資料洩漏** | 隨機切分、rolling 沒先 shift、未 groupby 就 shift | TimeSeriesSplit + Pipeline 封裝 + 三條鐵律 |
| **遞迴預測的分布偏移** | 訓練用真實 lag、推論用預測 lag → 離線指標虛高 | 改直接多步法，h 的模型只用 `lag_h` 以上 |
| **恆等式不一致** | 量、價、值各自預測 → 預測的量×價 ≠ 預測的值 | 只預測量與價，值用恆等式導出 |
| **平均指標掩蓋問題** | 大國把整體 MAE 平均掉 | 依稅號 / 規模 / horizon 分層報告 |
| **零膨脹** | 大量補 0 月份，L1 目標把預測往 0 拉 | tweedie 或二階段模型 |
| **樣本稀疏** | 小國單一品項只有零星幾筆 | `min_active_months: 24`，或併為「其他」 |
| **打不贏 baseline** | 複雜模型未必更好 | MASE < 1 才算贏；打不贏就誠實寫，這本身是有效結論 |
| **把管制當偏好** | 特徵重要度顯示中國大陸重要，誤讀成消費者偏好 | `is_regulated_source` flag + 分群排除 |

### 資料風險

| 風險 | 說明 | 因應 |
|---|---|---|
| **漏抓 4205 零食** | 單價最高的品類整個消失，目標變數偏誤 | 兩個核心號列都要抓 |
| **復運沒扣** | 高估進口需求 | 管道 A 分離復進口，或管道 B 選「不含復運」 |
| **稅號選錯** | 整份分析報廢 | Phase 0 花時間查證，理由寫進 config |
| **HS 版本斷點** | 2017 / 2022 改版造成序列不連續 | 建新舊對照表，或用事件 dummy 標記 |
| **無法自動更新** | 兩系統皆有驗證碼 | 接受人工季度更新，SOP 寫清楚 |
| **資訊保護遮罩** | 關務署對可能揭露個別廠商的資料做保護處理 | 檢查是否有異常空值或合併項 |
| **範圍蔓延** | 想同時做出口、動物用藥 | 嚴守本階段只做進口食品 |

---

## 🚀 快速開始

```bash
git clone <repo-url>
cd pet-import-forecast

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

```bash
# ⚠️ 第一步是人工的：依 docs/download_sop.md 下載 CSV 到 data/raw/

python -m src.data.parse_downloads
python -m src.data.clean
python -m src.features.build_features
python -m src.models.train --stage baseline   # baseline 一定要先跑
python -m src.models.train --stage all
```

```bash
pytest
```

### requirements.txt

```
pandas>=2.0
numpy
scikit-learn>=1.3
lightgbm
statsmodels
prophet
shap
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

> 原始資料不進版控：檔案大、且來源有使用條款。改為在 `MANIFEST.md` 記錄取得方式，讓他人可自行重建。

---

## 🔮 Phase 2 展望（本 repo 暫不實作）

- **出口機會分析**：以 UN Comtrade 鏡像資料建立「國家 × 品項」矩陣，
  用協同過濾 / SVD 推薦台灣尚未出口但目標市場偏好的品項
- **動物用藥需求**：資料結構差異大（受管制、有許可證制度、樣本稀疏），需獨立設計

**範圍界定**：本階段**只做進口、只做寵物食品**。

---

## 📄 License

MIT
