# 既存資産の棚卸し（~/projects からの流用）

**[← README（目次）](../README.md)** ・ 関連: [idea_catalog](idea_catalog.md) ・ [data_sources](data_sources.md) ・ [evaluation](evaluation.md) ・ [candidates](candidates/README.md)

ハッカソンで再利用できそうな自作プロジェクト。詳細は各プロジェクトの README / メモリ参照。

## 気象データ取得・可視化

| プロジェクト | 使える部分 | 対応アイデア |
|---|---|---|
| `jma_app_suite` 系 | 予報/レーダー/衛星/天気図の取得・表示（Vanilla JS） | ID-17, ID-21, ID-32 |
| `jma_mcp` `jma_mcp_remote` | JMA APIを叩くMCPサーバー（予報・アメダス・台風・潮位など） | ID-31 のツール層 |
| `jma_weather_report` | JMA APIから定期取得しレポート化（Python/Actions） | ID-31, ID-33 |
| `RAG_met` | 気象文書のRAG基盤 | ID-31, ID-32教材, ID-10（農薬ラベル） |
| `tide_viewer` | 沖縄県7観測所の潮位（tide_obs/astro/time、96点スライス注意） | ID-17 |
| `nouken` | 農研機構メッシュ農業気象データ・全天日射量の取得 | ID-01, ID-02, ID-10〜12 |
| `ageostrophic` `note_jra55_emagram` | 高層・再解析の解析ノウハウ、エマグラム | ID-32 |

## 電力・エネルギー

| プロジェクト | 使える部分 | 対応アイデア |
|---|---|---|
| `okiden` `okiden_month` `okiden_jukyu` | 電力使用量・電気代・受給電力の実績データと集計コード | ID-01, ID-03, ID-04 |
| `okiden_pages` | 電力データのWeb表示 | ID-01 のデモUI |

## 生成AI・自動レポート

| プロジェクト | 使える部分 | 対応アイデア |
|---|---|---|
| `ai_news` `econ_digest` | 定期データ→LLM要約→配信のパイプライン（Ollama/Haiku二段） | GA-01 全般, ID-24 |
| `weather_digest` 系（`ai_news`等に同構成） | 気象データのダイジェスト生成 | ID-01, ID-21 |
| `agent_orchestrator` | Sonnet=リーダー / ローカルLLM=部下、router/ledger/retry | ID-31 のエージェント基盤 |
| `local_agent` | ローカルLLM実行環境（Ollama） | GenAIのコスト0検証 |
| `claude_writing` | Claude Codeで文章を書くノウハウ | 成果物の記事化・発表資料 |
| `RAG_met` | （再掲）RAG | ID-31 |

## 台風

| プロジェクト | 使える部分 | 対応アイデア |
|---|---|---|
| `typhoon_track_dl` | 気象庁ベストトラック（構造化）、進路傾向のSOM | ID-14, CS-06 |
| `typhoon_wind_dl` | 台風中心付近の風速分布（ERA5）をCNN学習 | ID-14 |
| `typhoon_forecast_viewer` | 予報円・進路線のスマホ最適化表示（Vanilla JS） | ID-13, ID-14 のUI |

## 経済・家計

| プロジェクト | 使える部分 | 対応アイデア |
|---|---|---|
| `econ_digest` | 経済ニュースダイジェスト自動生成 | ID-24 |
| `portfolio_analyzer` `stock_analysis` | 資産横断集約・企業データ分析 | ID-24 |
| `kakeibo` | 口座・支出管理CLI | ID-03, ID-25 |

## その他

| プロジェクト | 使える部分 | 対応アイデア |
|---|---|---|
| `media_indexer` `lichens` | ローカル写真のExif・インデックス | ID-33（写真の日付→当日の天気） |
| `ml_forecast` `ml_forecast_pages` | 気象の機械学習予測の実装・公開ノウハウ | MM-01〜08 全般のたたき台 |
| `marp_slides` `ppt_auto` | 発表スライド自動生成 | ハッカソン発表資料 |
| `common/` | 共通ユーティリティ | 全般 |

## 特に効きそうな組み合わせ
- **ID-31（Q&Aエージェント）** = `jma_mcp` + `RAG_met` + `agent_orchestrator` — ほぼ土台が揃っている
- **ID-17（ビーチ日和）** = `tide_viewer` + `jma_app_suite` + digest系の文章生成
- **ID-01（再エネ＋需給）** = `okiden*` + `nouken`(日射) + `ai_news`のパイプライン
- **ID-14（台風運休）** = `typhoon_*` 3点セット
- **MM-01〜08** の実装は `ml_forecast` の既存コードを出発点にできる
