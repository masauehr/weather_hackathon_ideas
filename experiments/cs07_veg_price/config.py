"""CS-07 スパイクの設定値。

対象アイデア: ID-25 生鮮野菜価格の気象先行指標 / CS-07。
仮説: 主産地の日照時間の平年比が、2〜4週後の葉物卸売価格に先行する（日照↓ → 価格↑）。

品目を替えて再検証できるよう、CROPS に定義を並べて ACTIVE_CROP で選ぶ。
出力ファイルは品目スラッグで分ける（例: veg_price_spinach.csv, diagnostics_spinach.png）。
"""

from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "cs07"  # 生データ（.gitignore 済み）
OUT_DIR = Path(__file__).resolve().parent / "results"            # 図・集計（Git 追跡）

# --- 気象庁 過去の気象データ検索（etrn）の地点 ---
# prec_no = 都府県・地方コード, block_no = 地点コード。daily_s1.php（気象官署）は「日照時間」列を持つ。
JMA_STATIONS = {
    "suwa":     {"prec_no": 48, "block_no": "47620", "name": "諏訪（長野県）"},   # 夏秋レタス
    "shizuoka": {"prec_no": 50, "block_no": "47656", "name": "静岡（静岡県）"},   # 冬レタス
    "maebashi": {"prec_no": 42, "block_no": "47624", "name": "前橋（群馬県）"},   # ほうれんそう（関東平野・高冷地とも群馬が主力）
    "kumagaya": {"prec_no": 43, "block_no": "47626", "name": "熊谷（埼玉県）"},   # ほうれんそう（冬の関東）
    "tokyo":    {"prec_no": 44, "block_no": "47662", "name": "東京（参考・消費地）"},
}

# --- 品目定義（ベジ探 sch7.do 日別 outPutKbn=4 のコード） ---
#   city 101 = 関東ブロック 東京都（豊洲・大田・豊島・淀橋の4市場計）
#   ruibetu: 20=葉茎菜類, 30=洋菜類 / code: ベジ探の品目コード
CROPS = {
    "lettuce": {
        "price_item": "レタス",
        "vegetan_ruibetu": "30", "vegetan_code": "33400",
        "producer_station": "suwa",
    },
    "spinach": {
        "price_item": "ほうれんそう",
        "vegetan_ruibetu": "20", "vegetan_code": "31800",
        "producer_station": "maebashi",
    },
}
ACTIVE_CROP = "spinach"   # ← ここを切り替えて再検証（"lettuce" / "spinach"）

_c = CROPS[ACTIVE_CROP]
ITEM_SLUG = ACTIVE_CROP
PRICE_ITEM = _c["price_item"]
PRODUCER_STATION = _c["producer_station"]
VEGETAN_CITY = "101"
VEGETAN_ITEM_RUIBETU = _c["vegetan_ruibetu"]
VEGETAN_ITEM_CODE = _c["vegetan_code"]

# --- 取得期間 ---
YEAR_START = 2019          # 日照（平年比の分母を作るため長め）
YEAR_END = 2026            # 未来月はスクリプトが自動で打ち切る
VEG_YEAR_START = 2024      # ベジ探 日別は 2024年〜
VEG_YEAR_END = 2026

# 価格取得バックエンド: "vegetan_auto" / "manual" / "estat"
PRICE_BACKEND = "vegetan_auto"
STATS_DATA_ID = ""        # PRICE_BACKEND="estat" のときの statsDataId

# --- 解析 ---
LAG_WEEKS = list(range(0, 9))
GO_LAGS = [2, 3, 4]       # この範囲のいずれかで p<GO_P かつ ρ<0 なら GO
GO_P = 0.05
