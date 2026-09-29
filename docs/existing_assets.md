# 既存資産の棚卸し（~/projects からの流用）

**[← README（目次）](../README.md)** ・ 関連: [idea_catalog](idea_catalog.md) ・ [data_sources](data_sources.md) ・ [evaluation](evaluation.md) ・ [candidates](candidates/README.md)

ハッカソンで再利用できそうな自作プロジェクト（**公開リポジトリのみ**）。詳細は各プロジェクトの README / メモリ参照。

> ⚠️ ここに挙げるのは**コード・実装ノウハウの参考**。ハッカソンで使う**データ**は気象庁＋公開データのみ（[CLAUDE.md](../CLAUDE.md)）。
> 個人データ（自宅の電力使用量・電気代など）を持つプロジェクトは**データを流用しない**。

## 気象データ取得・可視化

| プロジェクト | 使える部分 | 対応アイデア |
|---|---|---|
| `jma_mcp` `jma_mcp_remote` | JMA APIを叩くMCPサーバー（予報・アメダス・台風・潮位など） | ID-31 のツール層 |
| `jma_weather_report` | JMA APIから定期取得しレポート化（Python/Actions） | ID-31, ID-33 |
| `RAG_met` | 気象文書のRAG基盤。**2026-09-28実機確認: `RAGQuery.ask()`が動作、ChromaDB(既に総観気象学教科書・気象庁予報用語集を投入済み)から検索し出典ページ付きで回答**（例: 「前線とは何か」→ 総観気象学p.168等を引用）。ID-32教材モードにそのまま使える。ただし`strict`モードは検索でヒットしない質問には「該当情報なし」で拒否するため、質問の言い回しを教科書の記述に近づける工夫が要る | ID-31, ID-32教材 |
| `tide_viewer` | 沖縄県7観測所の潮位（tide_obs/astro/time、96点スライス注意） | ID-17 |
| `ageostrophic` | 高層・再解析の解析ノウハウ、エマグラム | ID-32 |

ID-32のWeb UI（天気図・衛星の地図表示）は上記に該当する公開資産が無いため、別途新規に用意する（自作 or 軽量ライブラリ）方針。

## 生成AI・自動レポート

| プロジェクト | 使える部分 | 対応アイデア |
|---|---|---|
| `ai_news` `econ_digest` | 定期データ→LLM要約→配信のパイプライン（Ollama/Haiku二段） | GA-01 全般, ID-24 |
| `weather_digest` 系（`ai_news`等に同構成） | 気象データのダイジェスト生成 | ID-01, ID-21 |
| `local_agent` | ローカルLLM実行環境（Ollama） | GenAIのコスト0検証 |
| `claude_writing` | Claude Codeで文章を書くノウハウ | 成果物の記事化・発表資料 |
| `RAG_met` | （再掲）RAG | ID-31 |

## 台風

| プロジェクト | 使える部分 | 対応アイデア |
|---|---|---|
| `typhoon_track_dl` | 気象庁ベストトラック（構造化）、進路傾向のSOM。固定長テキストのパース仕様（`parse.py`）はID-35スパイクでも再実装して利用 | ID-14, CS-06, ID-35 |
| `typhoon_wind_dl` | CNNで風速分布を学習する実装の書き方（※本プロジェクトの気象データは気象庁に置き換え、ERA5は使わない） | ID-14 のコード参考 |
| `typhoon_forecast_viewer` | 予報円・進路線のスマホ最適化表示（Vanilla JS） | ID-13, ID-14 のUI |

## 経済・家計

| プロジェクト | 使える部分 | 対応アイデア |
|---|---|---|
| `econ_digest` | 経済ニュースダイジェスト自動生成 | ID-24 |

## その他

| プロジェクト | 使える部分 | 対応アイデア |
|---|---|---|
| `lichens` | ローカル写真のExif・インデックス | ID-33（写真の日付→当日の天気） |
| `marp_slides` `ppt_auto` | 発表スライド自動生成 | ハッカソン発表資料 |
| `common/` | 共通ユーティリティ | 全般 |

## 特に効きそうな組み合わせ
- **ID-31（Q&Aエージェント）** = `jma_mcp` + `RAG_met` — 土台の一部が揃っている
- **ID-17（ビーチ日和）** = `tide_viewer` + digest系の文章生成
- **ID-14（台風運休）** = `typhoon_*` 3点セット
