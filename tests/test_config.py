"""稅號設定的守門測試。

README 把「漏抓 4205 零食」列為第一號風險：單價最高的品類整個消失，
精緻化結論會失真。風險寫在文件裡沒有約束力，寫成會失敗的測試才有。
"""

from __future__ import annotations

import pytest

from src import config

# 防檢署「犬貓寵物食品輸入檢疫條件」定義的兩個核心號列
CORE_CODES = {"2309.10.00.00-2", "4205.00.90.10-4"}


def test_both_core_codes_confirmed():
    """兩個核心號列都必須是 confirmed —— 缺一不可。

    2309.10 是主食，4205.00 是皮製嚼咬零食（在皮革章第 42 章，不是食品章）。
    只抓 2309.10 的話，整個寵物零食品類會憑空消失。
    """
    codes = set(config.included_hs_codes())
    missing = CORE_CODES - codes
    assert not missing, (
        f"核心號列遺失：{missing}。\n"
        f"特別注意 4205.00.90.10-4 —— 寵物零食歸在皮革章，"
        f"漏掉它會讓精緻化結論嚴重低估。"
    )


def test_query_string_matches_sop():
    """產生的查詢字串要跟 docs/download_sop.md 裡的一致。

    SOP 要人工貼 `23091000002,42050090104` 到單一窗口。
    這個字串若跟 config 產生的對不上，就會下載到錯的資料。
    """
    assert config.hs_query_string() == "23091000002,42050090104"


def test_query_codes_are_11_digits():
    """CCC 號列必須是 11 位數字。

    打錯一碼查出來是完全不同的貨品，而且系統不會報錯 ——
    你會拿到一份看起來正常但完全錯誤的資料。在下載前擋下來。
    """
    for code in config.hs_query_string().split(","):
        assert code.isdigit() and len(code) == 11, f"非法 CCC 號列：{code}"


def test_display_and_query_forms_agree():
    """顯示格式（2309.10.00.00-2）去掉分隔符後應等於查詢格式。

    兩處各寫一次就有寫岔的可能，這裡強制它們一致。
    """
    cfg = config.load("hs_codes")
    for item in cfg["include"]:
        stripped = item["code"].replace(".", "").replace("-", "")
        assert stripped == item["code_query"], (
            f"{item['code']} 去分隔符後為 {stripped}，"
            f"但 code_query 是 {item['code_query']}"
        )


def test_invalid_ccc_rejected():
    """長度不對或含非數字的號列要被擋下。"""
    with pytest.raises(ValueError, match="11 位數字"):
        config._assert_valid_ccc(["2309100000"])      # 只有 10 碼
    with pytest.raises(ValueError, match="11 位數字"):
        config._assert_valid_ccc(["2309.10.00.00-2"]) # 忘了去分隔符


def test_start_ym_is_2016():
    """資料起點須為 2016-01。

    民國105年起採一般貿易制度，103–104 年為回溯資料、口徑不同。
    起點設錯會讓序列前段不可比，且不會有任何錯誤訊息。
    """
    assert config.load("params")["data"]["start_ym"] == "2016-01"


def test_reimport_excluded_by_default():
    """預設必須扣除復進口。

    國貨出口後退回也算進口，不扣會系統性高估台灣市場需求。
    """
    assert config.load("params")["clean"]["exclude_reimport"] is True


def test_regulated_countries_declared():
    """MP1 受管制來源不可為空。

    中國大陸僅開放乾狗糧（牛肉口味）。沒宣告這件事，
    模型會把法規限制學成市場偏好。
    """
    assert "中國大陸" in config.regulated_countries()
