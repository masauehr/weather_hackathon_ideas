# 第一次候補の詳細設計

**[← README（目次）](../../README.md)** ・ 関連: [evaluation](../evaluation.md) ・ [idea_catalog](../idea_catalog.md) ・ [genai_angles](../genai_angles.md) ・ [existing_assets](../existing_assets.md)

個別設計: [c32 天気図VLM解説](c32_weather_chart_vlm.md) ・ [c17 ビーチ日和プランナー](c17_beach_day_planner.md) ・ [c05 気象病アシスタント](c05_meteoropathy_assistant.md)

[../evaluation.md](../evaluation.md) で上位に来た3案を、ハッカソンで実際に作る前提で深掘りする。
いずれもコードは書かず、仕様・データ・デモ筋書き・リスクまで。

| ファイル | 案 | 一言 | 生成AIの核 |
|---|---|---|---|
| [c32_weather_chart_vlm.md](c32_weather_chart_vlm.md) | ID-32 天気図VLM解説 | 天気図・衛星画像を読み、気圧配置を判定して平文で解説＋読み方を教える | VLMの画像理解（GA-05） |
| [c17_beach_day_planner.md](c17_beach_day_planner.md) | ID-17 ビーチ日和＋観光プラン | 天気・波・潮位から「海日和スコア」を出し、半日プランを生成 | 予測値→行動提案の個別化（GA-04/GA-01） |
| [c05_meteoropathy_assistant.md](c05_meteoropathy_assistant.md) | ID-05 気象病アシスタント | 気圧変化からリスク指数を予測し、理由説明とセルフケアを対話で提供 | プロフィール×予測×助言（GA-04） |

## 3案の比較（48h開発視点）

| 観点 | ID-32 | ID-17 | ID-05 |
|---|---|---|---|
| データ入手 | 気象庁の画像のみ（◎） | Open-Meteo＋tide_viewer（◎） | Open-Meteo気圧のみ（◎） |
| ML実装量 | ほぼ無し（VLM＋軽い分類） | 中（スコア回帰、なくてもルールで可） | 中（ロジスティック回帰、教師データが課題） |
| 生成AI必然性 | 高（画像理解はVLM必須） | 中〜高（出し分け・プラン生成） | 高（個別化・対話） |
| デモ映え | 高（画像1枚で成立、教材に展開） | 高（地図・スコア・タイムライン） | 中（会話中心、視覚要素を足したい） |
| 既存流用 | jma_app_suite, RAG_met | tide_viewer, jma_app_suite, digest系 | 少ない（ゼロから） |
| 最大リスク | VLMの事実誤り | スコア式の妥当性・波データ精度 | 「効く」の根拠（教師データ・プラセボ） |
| 沖縄テーマ適合 | 中 | 高 | 中 |

## 共通の土台: ID-31 自然言語フロント
3案いずれも、UIの一部を「自然言語で質問 → データ取得 → 回答」にできる（[../idea_catalog.md](../idea_catalog.md) ID-31）。
チーム戦なら ID-31 を共通基盤にして各案を機能として載せる構成も検討する。詳細は各ファイルの「ID-31との統合」節。

## 次のアクション
1. この3案から要項・審査基準に照らして1案に絞る（[../evaluation.md](../evaluation.md) の再計算）
2. 選んだ案の「MVPスコープ」だけに集中してプロトタイプ
3. [../correlation_studies.md](../correlation_studies.md) の該当検証（ID-17→CS-05周辺、ID-05→CS-03/CS-10）を先に回して前提を確認
