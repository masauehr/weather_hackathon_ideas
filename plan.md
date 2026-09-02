# plan.md — 次の一手

**[← README（目次）](README.md)** ・ 関連: [evaluation](docs/evaluation.md) ・ [candidates](docs/candidates/README.md) ・ [correlation_studies](docs/correlation_studies.md) ・ [data_sources](docs/data_sources.md)

## 確定要項（ハッカソン情報が判明したら埋める）

- 名称 / 主催:
- 日程・開発時間:
- テーマ・お題:
- 利用可能API・提供データ・提供枠（クラウド/API クレジット等）:
- 審査基準（配点）:
- チーム構成 / 個人:
- 提出物（デモ・スライド・リポジトリ）:

> 判明後: [docs/evaluation.md](docs/evaluation.md) の評価軸の重みを審査基準に合わせて更新する。

---

## フェーズ1: アイデア発散（済 / 継続）
- [x] フォルダ・ドキュメント一式作成（2026-09-02）
- [x] [docs/idea_catalog.md](docs/idea_catalog.md) に36案＋種を列挙
- [ ] 思いついた案を随時 idea_catalog に追記（ID連番を維持）

## フェーズ2: 事前準備（要項を待たずに進められる）
- [ ] Open-Meteo 取得ユーティリティを1本書く（地点・期間・変数指定 → DataFrame）
- [ ] Copernicus CDS アカウント＋APIキー取得（ERA5）
- [ ] ODPT 開発者登録、Bluesky アプリパスワード発行
- [ ] `nouken` のメッシュ農業気象データ取得コードを動く状態に復旧
- [ ] `jma_mcp` / `RAG_met` / `agent_orchestrator` をローカルで起動確認（ID-31 土台）
- [ ] ローカルLLM（Ollama）でナレーション品質の当たりを見る（GA-01 を1例）
- [ ] `requirements.txt` 雛形（pandas, lightgbm, statsmodels, requests, matplotlib, openmeteo-requests, shap）

## フェーズ3: 相関の当たり付け（上位候補について）
- [ ] [docs/correlation_studies.md](docs/correlation_studies.md) から3件選んで実施
  - 第一次候補に対応: CS-01/CS-02（ID-01）、CS-03/CS-10（ID-05）、CS-05（ID-17周辺）
- [ ] 各 GO/NO-GO を記録（`experiments/` にノートブック、`data/` は git 除外）

## フェーズ4: 選抜とデモ設計
- [x] 第一次候補3案の詳細設計（[docs/candidates/](docs/candidates/)：ID-32 / ID-17 / ID-05）— 2026-09-02
- [ ] 評価表を再計算し1案に決定
- [ ] 「3分で伝わる」デモ筋書き（課題→入力→予測→生成AIの一言→行動）を書く ※各candidateに草案あり
- [ ] 必要な既存資産を実際に組み込めるか30分スパイク

## フェーズ5: ハッカソン当日
- [ ] MVP実装（スコープは1機能に固定、拡張は後回し）
- [ ] ガードレール実装（数値は引用のみ・免責文・不確実性表示）
- [ ] スライド（`marp_slides` or `ppt_auto`）、リポジトリ整備

---

## 進めるうえでの原則
- 実装フェーズに入るまでコードを書かない。まずMD。
- データは「最小・手集めでも可」から。完璧なデータセットを待たない。
- GPU前提・巨大モデル前提のアイデアは当日スコープから外す。
- 生成AIの必然性を毎回言語化する。無くても成立するなら別案を優先。

## メモ / 未決事項
- ハッカソンが「沖縄開催 or 沖縄テーマ」なら ID-17 / ID-01 の地域性が加点されうる
- チーム戦なら ID-31 を共通基盤にして複数機能を分担する構成も可
- X API を使う案（ID-22）は Bluesky 代替で設計し直すこと
