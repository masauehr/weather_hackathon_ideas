# experiments/ — 検証コード

**[← README（目次）](../README.md)**

アイデアを本設計する前の「相関があるか」を数時間で確かめる小規模スパイク置き場。

## ルール
- 気象データは **気象庁** から取得（[CLAUDE.md](../CLAUDE.md)）。相手側は **公開データのみ**、個人データ不可。
- 生データは `data/`（`.gitignore` 済み）。コミットするのはコードと結果メモ（`README.md`）だけ。
- 実行環境は conda env `met_env`（Python 3.11）。ルートの [requirements.txt](../requirements.txt) 参照。
- 図表には「気象庁ホームページ」等の出典を明記。

## 一覧
| ディレクトリ | 対応アイデア | 内容 | 状態 |
|---|---|---|---|
| [cs07_veg_price/](cs07_veg_price/)（結果まとめ: [SPINACH_FINDINGS.md](cs07_veg_price/SPINACH_FINDINGS.md)） | [ID-25](../docs/idea_catalog.md) / [CS-07](../docs/correlation_studies.md) | 産地の気象 → 数週後の葉物卸売価格 の先行性 | **一部GO（2026-09-02）**。日照のみ=NO-GO → 気象4特徴 → ほうれんそう×真夏日数(前橋) → 15年月次 ρ=+0.34 → **分布ラグ回帰(HAC)で季節・トレンド・AR1・降水を統制しても hot_anom_L1 β=+0.0096, t=+3.3, p=0.001（真夏日+10日→翌月価格+約10%）** → 産地合成(7官署)でも不変、**入荷量の回帰で真夏日→供給減 t=−4.6/−3.2（真夏日+10日→入荷量−15%）＝価格上昇は供給減が経路**。直接被害と作付け判断は月次では分離不能。**月次 Yes/No の早期警戒アラートとしては弱い（トレンド除去後 AUC≈0.55, リフト≈1.0）** — 連続効果は本物だが2値には落ちない。レタスは終了。結果まとめ [SPINACH_FINDINGS.md](cs07_veg_price/SPINACH_FINDINGS.md) |
| ~~cs32_chart_vlm/~~ | [ID-32](../docs/candidates/c32_weather_chart_vlm.md) | 天気図・衛星赤外をVLMに読ませ、実況・予報でガードレール検証＋複数事例での正答率測定 | **一部GO → 独立プロジェクトとして切り出し済み（2026-09-29）**。[weather_chart_vlm](https://github.com/masauehr/weather_chart_vlm)（[デモ](https://masauehr.github.io/weather_chart_vlm/webui/index.html)）を参照。気象庁の天気図/衛星/アメダス取得〜検証の配管は成立、実際のClaude API（Sonnet 5）で当日1事例NG0件・$0.018/回。気象庁「日々の天気図」アーカイブから15事例（7パターン）で正答率67%（10/15）・$0.065。台風・梅雨前線・移動性高気圧は強いが「日本海低気圧⇄南岸低気圧」を系統的に混同 |
| ~~id15_dry_route/~~ | [ID-15](../docs/idea_catalog.md) | 高解像度降水ナウキャストで、経路上の各点が濡れるかを判定し出発時刻を提案 | **一部GO → 独立プロジェクトとして切り出し済み（2026-09-29）**。[dry_route](https://github.com/masauehr/dry_route) を参照。ナウキャストタイルのαチャンネルだけで降雨の有無を機械的に判定できることを実測で確認、奄美市名瀬（帯状のレーダーエコー接近中）の実データで出発をずらす効果を確認（20分後だけ40%濡れ、他は0%）。OSRMで道路にスナップした経路にも対応、Webアプリ（Leaflet地図＋server.py）も実装済み |
