"""CS-07 スパイクの設定値。

対象アイデア: ID-25 生鮮野菜価格の気象先行指標 / CS-07。
当初仮説: 主産地の日照時間の平年比が、2〜4週後の葉物卸売価格に先行する（日照↓ → 価格↑）。
拡張: 日照だけでなく 全天日射量・降水量・高温日数 も気象特徴に加えて調べる。

品目を替えて再検証できるよう CROPS に定義を並べ ACTIVE_CROP で選ぶ。
出力ファイルは品目スラッグで分ける（veg_price_<crop>.csv, lag_corr_<crop>.png ...）。
"""

from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "cs07"  # 生データ（.gitignore 済み）
OUT_DIR = Path(__file__).resolve().parent / "results"            # 図・集計（Git 追跡）

# --- 気象庁 過去の気象データ検索（etrn）の地点 ---
# prec_no = 都府県・地方コード, block_no = 地点コード。daily_s1.php（気象官署）は「日照時間」列を持つ。
JMA_STATIONS = {
    # name の末尾 [日射] は全天日射量の観測がある官署（etrn a3 で取得可）
    "nagano":   {"prec_no": 48, "block_no": "47610", "name": "長野（長野県）[日射]"},  # 夏秋レタス（南佐久の代表として）
    "suwa":     {"prec_no": 48, "block_no": "47620", "name": "諏訪（長野県）"},
    "shizuoka": {"prec_no": 50, "block_no": "47656", "name": "静岡（静岡県）[日射]"},
    "tokyo":    {"prec_no": 44, "block_no": "47662", "name": "東京（参考・消費地）[日射]"},
    # --- ほうれんそう産地（東京入荷ウェイト: 群馬36/茨城27/栃木11/埼玉8/千葉8/岩手4/岐阜2 %）---
    "maebashi": {"prec_no": 42, "block_no": "47624", "name": "前橋（群馬県）[日射]"},
    "mito":     {"prec_no": 40, "block_no": "47629", "name": "水戸（茨城県）"},
    "utsunomiya": {"prec_no": 41, "block_no": "47615", "name": "宇都宮（栃木県）"},
    "kumagaya": {"prec_no": 43, "block_no": "47626", "name": "熊谷（埼玉県）"},
    "chiba":    {"prec_no": 45, "block_no": "47682", "name": "千葉（千葉県）"},
    "morioka":  {"prec_no": 33, "block_no": "47584", "name": "盛岡（岩手県）"},
    "gifu":     {"prec_no": 52, "block_no": "47632", "name": "岐阜（岐阜県）[日射]"},
}
# 産地キー → 都道府県名（ベジ探の origin 表記に一致）
STATION_PREF = {
    "maebashi": "群馬", "mito": "茨城", "utsunomiya": "栃木", "kumagaya": "埼玉",
    "chiba": "千葉", "morioka": "岩手", "gifu": "岐阜",
}

# --- 品目定義（ベジ探 sch7.do 日別 outPutKbn=4 のコード） ---
#   city 101 = 関東ブロック 東京都（豊洲・大田・豊島・淀橋の4市場計）
#   ruibetu: 20=葉茎菜類, 30=洋菜類 / code: ベジ探の品目コード
CROPS = {
    "lettuce": {
        "price_item": "レタス",
        "vegetan_ruibetu": "30", "vegetan_code": "33400",
        "producer_station": "nagano",   # 日射観測あり（諏訪には無いため長野に変更）
    },
    "spinach": {
        "price_item": "ほうれんそう",
        "vegetan_ruibetu": "20", "vegetan_code": "31800",
        "producer_station": "maebashi",
    },
}
ACTIVE_CROP = "spinach"   # ← "spinach" のみ進行中（lettuce は 2026-09-02 終了）

_c = CROPS[ACTIVE_CROP]
ITEM_SLUG = ACTIVE_CROP
PRICE_ITEM = _c["price_item"]
PRODUCER_STATION = _c["producer_station"]
VEGETAN_CITY = "101"
VEGETAN_ITEM_RUIBETU = _c["vegetan_ruibetu"]
VEGETAN_ITEM_CODE = _c["vegetan_code"]

# --- 取得期間 ---
YEAR_START = 2011          # 気象（月次の長期系列に合わせて拡張）
YEAR_END = 2026            # 未来月はスクリプトが自動で打ち切る
VEG_YEAR_START = 2024      # ベジ探 日別は 2024年〜
VEG_YEAR_END = 2026

# ベジ探 月別（outPutKbn=1）＝1984年〜。真夏日数×価格の長期検証用。
VEG_MONTHLY_YEAR_START = 2011
VEG_MONTHLY_YEAR_END = 2026
# 月別モードのコード（day モードと別体系）: marketCode 7=東京都中央市場計
VEGETAN_MARKET_MONTHLY = "7"
VEGETAN_RUIBETU_MONTHLY = {"lettuce": "9999030", "spinach": "9999020"}[ACTIVE_CROP]
VEGETAN_CODE_MONTHLY = {"lettuce": "334000", "spinach": "318000"}[ACTIVE_CROP]

# 価格取得バックエンド: "vegetan_auto" / "manual" / "estat"
PRICE_BACKEND = "vegetan_auto"
STATS_DATA_ID = ""        # PRICE_BACKEND="estat" のときの statsDataId

# --- 気象特徴量 ---
# 週次で作る特徴（jma_daily_<station>.csv から）。名前=表示ラベル。
#   sunshine: 日照時間の週合計 / precip: 降水量の週合計 / solar: 全天日射量の週合計
#   hot30: 最高気温>=30℃ の日数（週） / hot25: >=25℃ の日数（週）
WEATHER_FEATURES = ["sunshine", "solar", "precip", "hot30", "hot25"]
HOT_THRESHOLDS = {"hot30": 30.0, "hot25": 25.0}

# --- 解析 ---
LAG_WEEKS = list(range(0, 9))
GO_LAGS = [2, 3, 4]       # この範囲のいずれかで p<GO_P かつ ρ<0 なら GO（日照の当初仮説）
GO_P = 0.05
