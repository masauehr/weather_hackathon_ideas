# 既存資産の棚卸し（~/projects からの流用）

**[← README（目次）](../README.md)** ・ 関連: [idea_catalog](idea_catalog.md) ・ [data_sources](data_sources.md) ・ [evaluation](evaluation.md) ・ [candidates](candidates/README.md)

ハッカソンで再利用できそうな自作プロジェクト。詳細は各プロジェクトの README / メモリ参照。

> ⚠️ ここに挙げるのは**コード・実装ノウハウの参考**。ハッカソンで使う**データ**は気象庁＋公開データのみ（[CLAUDE.md](../CLAUDE.md)）。
> 個人データを持つプロジェクト（`okiden*` の自宅電力実績など）は**データを流用しない**。コードの書き方だけ参考にする。

## 気象データ取得・可視化

| プロジェクト | 使える部分 | 対応アイデア |
|---|---|---|
| `jma_app_suite` 系 | 予報/レーダー/衛星の取得・表示（Vanilla JS）。**天気図（地上気圧配置図）の表示アプリは無い**（2026-09-28実機確認、apps/配下はforecast/radar系/satellite系のみ）。CSS/レイアウトの流儀のみ流用見込み | ID-17, ID-21 |
| `~/web/webapp/weatherChartGmsViewer`（`~/projects`外・個人作成） | **天気図・衛星の本格ビューア**（2026-09-28発見・実機確認）。OpenLayersで地図上に天気図(日本周辺/アジア域)・ひまわり衛星(赤外/可視/水蒸気)・降水レーダーを重ね合わせ表示。ズーム・海岸線・緯度経度グリッド・解析日時選択つき。取得元URLは本スパイクのfetch_chart.pyと同じbosai系（`himawari/data/satimg/...`等）。CORS回避用のPHPプロキシ（`cgi/get_contents.php`）も同梱、社内ネットワーク向けの分岐が入っているが自宅環境では素通しのfile_get_contentsとして動く | ID-32のUI本体として最有力 |
| `jma_mcp` `jma_mcp_remote` | JMA APIを叩くMCPサーバー（予報・アメダス・台風・潮位など） | ID-31 のツール層 |
| `jma_weather_report` | JMA APIから定期取得しレポート化（Python/Actions） | ID-31, ID-33 |
| `RAG_met` | 気象文書のRAG基盤。**2026-09-28実機確認: `RAGQuery.ask()`が動作、ChromaDB(既に総観気象学教科書・気象庁予報用語集を投入済み)から検索し出典ページ付きで回答**（例: 「前線とは何か」→ 総観気象学p.168等を引用）。ID-32教材モードにそのまま使える。ただし`strict`モードは検索でヒットしない質問には「該当情報なし」で拒否するため、質問の言い回しを教科書の記述に近づける工夫が要る | ID-31, ID-32教材, ID-10（農薬ラベル） |
| `tide_viewer` | 沖縄県7観測所の潮位（tide_obs/astro/time、96点スライス注意） | ID-17 |
| `nouken` | メッシュ農業気象データ取得コードの書き方（※気象データ本体は気象庁 obsdl から取得する方針） | ID-10〜12 のコード参考 |
| `ageostrophic` `note_jra55_emagram` | 高層・再解析の解析ノウハウ、エマグラム | ID-32 |

## 電力・エネルギー

| プロジェクト | 使える部分 | 対応アイデア |
|---|---|---|
| `okiden` `okiden_month` `okiden_jukyu` | **⚠️ 個人データ（自宅の使用量・電気代）につきデータは使用不可。** 集計・可視化コードの書き方のみ参考 | ID-01, ID-03 のコード参考 |
| `okiden_pages` | 電力データのWeb表示レイアウトの参考 | ID-01 のデモUIの参考 |

> ID-01/ID-03 で使う電力データは、**電力会社の公開実績**（でんき予報／過去の電力使用実績）と**一般送配電のエリア需給実績**（電源別の再エネ出力込み）に置き換える。

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
| `typhoon_wind_dl` | CNNで風速分布を学習する実装の書き方（※本プロジェクトの気象データは気象庁に置き換え、ERA5は使わない） | ID-14 のコード参考 |
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
- **ID-01（再エネ＋需給）** = 電力会社の公開実績＋エリア需給実績（データ）＋ 気象庁 obsdl の日射（データ）＋ `nouken`/`ai_news` のコード参考
- **ID-14（台風運休）** = `typhoon_*` 3点セット
- **MM-01〜08** の実装は `ml_forecast` の既存コードを出発点にできる
