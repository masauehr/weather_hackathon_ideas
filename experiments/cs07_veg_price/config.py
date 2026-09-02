"""CS-07 スパイクの設定値。

対象アイデア: ID-25 生鮮野菜価格の気象先行指標 / CS-07。
仮説: 主産地の日照時間の平年比が、2〜4週後のレタス等の卸売価格に先行する（日照↓ → 価格↑）。
"""

from pathlib import Path

# 生データの保存先（リポジトリルートの data/、.gitignore 済み）
DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "cs07"
OUT_DIR = Path(__file__).resolve().parent / "out"  # 図・集計の出力（.gitignore 済み: experiments/**/data ではないので注意）

# --- 気象庁 過去の気象データ検索（etrn）の地点 ---
# prec_no = 都府県・地方コード, block_no = 地点コード。
# 参照: https://www.data.jma.go.jp/stats/etrn/select/prefecture00.php
# daily_s1.php（気象官署）は「日照時間」列を持つ。アメダスのみの地点（daily_a1.php）は日照が無いことがある。
JMA_STATIONS = {
    # レタス: 夏秋は長野（諏訪）、冬は静岡。まずは諏訪で通年を取り、静岡は冬レタス期の補助。
    "suwa":     {"prec_no": 48, "block_no": "47620", "name": "諏訪（長野県）"},
    "shizuoka": {"prec_no": 50, "block_no": "47656", "name": "静岡（静岡県）"},
    "tokyo":    {"prec_no": 44, "block_no": "47662", "name": "東京（参考・消費地）"},
}
# 今回の主対象（価格に対する先行指標として使う産地）
PRODUCER_STATION = "suwa"

# 取得期間（年）。平年比の分母を作るためできるだけ長め。
YEAR_START = 2019
YEAR_END = 2026  # 価格データ（ベジ探 日別=2024〜）に合わせて最新まで。未来月はスクリプトが自動で打ち切る

# --- 価格データ ---
# item: 卸売価格の品目名（ベジ探 / e-Stat の表記に合わせる）
PRICE_ITEM = "レタス"

# 価格取得のバックエンド: "vegetan_auto" / "manual" / "estat"
#   vegetan_auto: ベジ探を自動取得（鍵不要・1リクエスト=1か月）。日別は2024年〜。
#   manual      : data/cs07/ の veg_price_manual.csv（列 date,price）か SCH*.csv を読む。
#   estat       : e-Stat API（要 ESTAT_APP_ID と STATS_DATA_ID）。
PRICE_BACKEND = "vegetan_auto"

# ベジ探 sch7.do（日別 outPutKbn=4）のコード
#   city           : 101=関東ブロック 東京都（豊洲・大田・豊島・淀橋の4市場計）
#   hinmokuRuibetu : 30=洋菜類
#   hinmokuCode    : 33400=レタス（334100=サニーレタス, 334600=リーフレタス）
VEGETAN_CITY = "101"
VEGETAN_ITEM_RUIBETU = "30"
VEGETAN_ITEM_CODE = "33400"

# ベジ探・日別データの取得期間（日別は2024年〜のみ）
VEG_YEAR_START = 2024
VEG_YEAR_END = 2026

# e-Stat: 青果物卸売市場調査 等の statsDataId（PRICE_BACKEND="estat" のとき）
STATS_DATA_ID = ""

# --- 解析 ---
LAG_WEEKS = list(range(0, 9))  # 0〜8週のラグを見る
# GO 判定: ラグ 2〜4 週のいずれかで、季節調整後に有意な負の相関（p < 0.05, ρ < 0）
GO_LAGS = [2, 3, 4]
GO_P = 0.05
