# データ取得が容易な相関テスト候補（1年分以上）

**[← README（目次）](../README.md)** ・ 関連: [correlation_studies](correlation_studies.md) ・ [data_sources](data_sources.md) ・ [ml_models](ml_models.md) ・ [idea_catalog](idea_catalog.md)

第一次候補（ID-32 / ID-17 / ID-05）に縛られず、「**最低1年分の実データ**が**すぐ・軽量に**手に入る」ものから相関テスト→機械学習を回すための候補。
**GRIB / NetCDF など大容量バイナリは除外**。すべて API（JSON）または CSV で、1地点あたり数百KB〜数MB。

## 気象側は Open-Meteo Historical Weather API で共通化

- エンドポイント: `https://archive-api.open-meteo.com/v1/archive`（`/v1/archive`）
- 1940年以降・全球・**1時間値**、ERA5/ERA5-Land ベースの再解析。**APIキー不要・非商用無料**（〜1万req/日）
- 1地点×数年×複数変数が**1リクエスト・数秒・JSON**で取れる。GRIBを一切触らずに済むのが要点
- 主な変数: `temperature_2m` `relative_humidity_2m` `surface_pressure` `shortwave_radiation` `wind_speed_10m` `precipitation` `cloud_cover`
- 商用利用や大量取得時はライセンス確認（CC-BY、商用は要問い合わせ）

---

## 容易さランキング

| 順位 | テスト | 気象側 | 相手側 | 相手側の形式・期間 | 整形の手間 |
|---|---|---|---|---|---|
| 1 | 気温 × 電力需要（沖縄エリア） | Open-Meteo archive（那覇） | 沖縄電力「過去の電力使用実績」 | 月別CSV・2018年〜・1時間値 | 小（結合するだけ） |
| 2 | 日射量 × 太陽光発電実績 | Open-Meteo archive（`shortwave_radiation`） | 一般送配電「エリア需給実績」 | CSV/年度zip・2016年度〜・1時間値・電源別列 | 中（CSV仕様の把握） |
| 3 | 気温・絶対湿度 × インフルエンザ流行 | Open-Meteo archive（県庁所在地） | 感染症発生動向調査（定点当たり報告数） | CSV・多年・週次 | 中（週次集約・絶対湿度計算） |

---

## テスト1 ── 気温 × 電力需要（沖縄エリア）　【最も容易】

対応アイデア: [ID-01](idea_catalog.md) / [ID-03](idea_catalog.md)、[CS-01](correlation_studies.md) の実データ版。

### データ
| | 気象 | 電力需要 |
|---|---|---|
| 取得元 | Open-Meteo Historical Weather API | 沖縄電力「過去の電力使用実績」 <https://www.okiden.co.jp/denki/dl/> |
| 期間 | 1940年〜（今回は2018年〜で十分） | **2018年〜**現在、月別 |
| 粒度 | 1時間 | 1時間（使用実績・使用率） |
| 形式・容量 | JSON・1リクエスト・数MB | CSV・月1ファイル・各数十KB |
| 取得方法 | `latitude=26.21&longitude=127.68&start_date=2019-01-01&end_date=2024-12-31&hourly=temperature_2m,relative_humidity_2m,shortwave_radiation` | ページから月別CSVをDL（数十ファイル）。仕様は <https://www.okiden.co.jp/denki/data_desc.html> |

### 相関仮説
- 日最高気温・各時刻気温とエリア需要は**非線形（V字/J字）**。夏は冷房で急増、冬は暖房で微増。
- 冷房度日(CDD)・暖房度日(HDD)で概ね説明できる。平日/休日、時間帯で層別が効く。

### 最小分析 → GO基準
1. 時刻を合わせて結合、散布図（気温 vs 需要）＋ LOWESS
2. CDD/HDD を作って単回帰、平日・休日で層別
3. LightGBM（分位点 P10/P50/P90）で当日〜翌日需要、ベースライン（季節Naive）と比較
- **GO**: CDD 単回帰で R² > 0.6、GBDT の MAPE がベースラインを明確に下回る

### 既存流用
`okiden` `okiden_month` `okiden_jukyu`（実績データと集計コード）、`nouken`（日射取得）

### 容易さの理由 / 注意
- 両側とも**公式・軽量・整形不要に近い**。年数も潤沢。相関が強く既知なのでデモが確実に動く。
- 注意: CSVの列定義（速報/確報、使用率の分母）を `data_desc` で確認。連休・イベント日の外れ値。

---

## テスト2 ── 日射量 × 太陽光発電実績

対応アイデア: [ID-02](idea_catalog.md)、[MM-02](ml_models.md)、[CS-02](correlation_studies.md) の実データ版。

### データ
| | 日射量 | 太陽光発電実績 |
|---|---|---|
| 取得元 | Open-Meteo archive `shortwave_radiation`（全天日射 W/m²）。代替 NASA POWER | 一般送配電「エリア需給実績」（電源別に**太陽光実績**の列あり） |
| 候補エリア | エリア代表点（例: 九州＝福岡付近） | 九州電力送配電 <https://www.kyuden.co.jp/td_area_jukyu/jukyu.html> / 東京電力PG <https://www.tepco.co.jp/forecast/html/area_jukyu-j.html> / 東北電力NW <https://setsuden.nw.tohoku-epco.co.jp/download.html> |
| 期間 | 1940年〜 | **2016年度〜**（各社）、月次CSV or 年度zip |
| 粒度 | 1時間 | 1時間値（元データは30分値の平均） |
| 形式・容量 | JSON・1リクエスト | CSV（月次）/ zip（年度）・合計数MB |

### 相関仮説
- エリア日射量とエリア太陽光出力は**ほぼ線形**。気温（パネル効率）・季節（日射角）で小さく補正。

### 最小分析 → GO基準
1. 時刻結合、時間値の散布図と相関 r
2. 物理式（GHI→出力の簡易変換）をベースライン、**残差を GBDT** で学習（気温・太陽高度・季節）
3. 快晴日 / 曇天日 / 変動日に分けて MAE を報告
- **GO**: 時間値 r > 0.85、ハイブリッドが物理式のみより nMAE 改善

### 既存流用
`nouken`（日射データ取得ノウハウ）、`okiden_pages`（表示UI）

### 容易さの理由 / 注意
- CSVを数回DLするだけで1年以上。関係がクリーンで**ML の教材として映える**。
- 注意: 各社でCSVレイアウトが違う。1エリアに絞る。太陽光「実績」列と「抑制量」の扱いを確認。沖縄は太陽光比率が低めなので九州エリアが題材向き。

---

## テスト3 ── 気温・絶対湿度 × インフルエンザ流行

対応アイデア: [idea_catalog I欄の種（媒介・感染症）](idea_catalog.md) / [ID-28](idea_catalog.md) 隣接。古典的な「絶対湿度仮説」の再現。

### データ
| | 気象 | インフルエンザ |
|---|---|---|
| 取得元 | Open-Meteo archive（対象都県の県庁所在地）。相対湿度＋気温＋気圧から**絶対湿度**を計算 | 感染症発生動向調査「定点当たり報告数」 |
| 具体源 | 〃 | 東京都感染症情報センター WEB感染症発生動向（CSVダウンロード、2000年1週〜） <https://idsc.tmiph.metro.tokyo.lg.jp/survey/websurvey/> / 厚労省 定点当たり報告数の推移 <https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/houkokusuunosuii_00007.html> |
| 期間 | 1940年〜 | **多年（20年以上）**、週次 |
| 形式・容量 | JSON | CSV・数百KB |

### 相関仮説
- **低温かつ低絶対湿度**の週の数週後にインフルエンザ定点報告数が増える（Shaman & Kohn の絶対湿度仮説）。
- 季節性が強いので、季節ダミーとの交絡を切り分けるのがポイント。

### 最小分析 → GO基準
1. 気象を**週平均**に集約、絶対湿度を算出
2. 絶対湿度・気温の**ラグ（1〜4週）**を特徴量に、定点報告数を回帰（負の二項 or GBDT、Tweedie）
3. 「増加/減少」の方向的中率、ピーク週の予測ズレで評価
- **GO**: ラグ2〜4週で絶対湿度の負の係数が有意、方向的中率 > 0.7

### 既存流用
直接の資産は薄い。`ai_news` / `econ_digest` の「定期取得→集計→生成」パイプライン雛形のみ。

### 容易さの理由 / 注意
- 両側CSVで通年・多年。**相関は非常に明確**でテストとして手堅い。
- 注意: 週の定義（第○週）を気象側と揃える。定点数の変更、コロナ禍（2020〜2022）の異常シーズンは除外 or フラグ。

---

## 補欠（次点。軽いが癖がある）

| テスト | 気象 | 相手側 | 癖 |
|---|---|---|---|
| 気圧変化 × 「頭痛」検索トレンド（[CS-03](correlation_studies.md)） | Open-Meteo `surface_pressure` | Google トレンド（CSVエクスポート or pytrends、週次5年） | pytrends は非公式で不安定。CSV手動DLなら容易。指標は相対値 |
| 気温 × JEPXスポット価格（[ID-02](idea_catalog.md)） | Open-Meteo（広域数地点） | JEPX 取引結果CSV（無料DL、30分値、年単位） | 価格は多要因（燃料費・出力抑制・連系線）。天候単独の寄与は小さめ |
| WBGT × 熱中症搬送（[CS-04](correlation_studies.md)） | Open-Meteo＋WBGT近似計算 | 消防庁「熱中症による救急搬送状況」週報CSV | **夏季のみ**で通年データにならない。熱順化の扱いが必要 |

---

## 進め方の提案

1. **テスト1 を最初に**回して「Open-Meteo archive 取得ユーティリティ」を1本作る（他テストでも使い回す）
2. GO したらそのまま [ml_models.md](ml_models.md) の該当モデルへ
3. テスト2・3 は取得ユーティリティが出来ていれば相手側CSVの整形だけ
4. 実装コードは `experiments/<test名>/`、生データは `data/`（`.gitignore` 済み）

## 出典
- [Historical Weather API | Open-Meteo](https://open-meteo.com/en/docs/historical-weather-api)
- [過去の電力使用実績｜でんき予報｜沖縄電力](https://www.okiden.co.jp/denki/dl/) ／ [データの説明](https://www.okiden.co.jp/denki/data_desc.html)
- [エリア需給実績データ｜九州電力送配電](https://www.kyuden.co.jp/td_area_jukyu/jukyu.html) ／ [東京電力PG](https://www.tepco.co.jp/forecast/html/area_jukyu-j.html) ／ [東北電力NW](https://setsuden.nw.tohoku-epco.co.jp/download.html)
- [WEB感染症発生動向調査｜東京都感染症情報センター](https://idsc.tmiph.metro.tokyo.lg.jp/survey/websurvey/) ／ [定点当たり報告数の推移｜厚生労働省](https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/houkokusuunosuii_00007.html)
