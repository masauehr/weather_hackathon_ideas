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
- [ ] **気象庁「過去の気象データ・ダウンロード」の操作に慣れる**（地点・項目・期間の選択、容量上限→分割DL）
- [ ] 気象庁 obsdl の CSV を読み込み・結合するユーティリティを1本書く（全テスト共通、`data/` は git 除外）
- [ ] 相手側の公開CSVを試しに1年分DL（電力使用実績／エリア需給実績／感染症週報）
- [ ] `jma_mcp` / `RAG_met` / `agent_orchestrator` をローカルで起動確認（ID-31 土台のコード参考）
- [ ] ローカルLLM（Ollama）でナレーション品質の当たりを見る（GA-01 を1例）
- [ ] `requirements.txt` 雛形（pandas, lightgbm, statsmodels, requests, matplotlib, shap）
- [ ] （交通系を使うなら）ODPT 開発者登録 ／ （農業系なら）農研機構データの利用申請

## フェーズ3: 相関の当たり付け（データ取得が容易な順）
- [ ] [docs/data_easy_tests.md](docs/data_easy_tests.md) の3件を上から実施
  - テスト1: 気温 × 電力需要（[CS-01](docs/correlation_studies.md)）
  - テスト2: 全天日射量 × 太陽光発電実績（[CS-02](docs/correlation_studies.md)）
  - テスト3: 気温・絶対湿度 × インフルエンザ流行
- [ ] 気象は気象庁 obsdl、相手側は公開データのみ。個人データは使わない
- [ ] 各 GO/NO-GO を記録（`experiments/<test名>/` にノートブック、`data/` は git 除外）

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
- **気象データは気象庁から。相手側は誰でもアクセスできる公開データのみ。個人データ・非公開データは使わない**（[CLAUDE.md](CLAUDE.md)）。
- GRIB（数値予報GPV）は容量のため扱わない。予測が要るところは気象庁 bosai の予報値で代替。
- 実装フェーズに入るまでコードを書かない。まずMD。
- データは「最小・手集めでも可」から。完璧なデータセットを待たない。
- GPU前提・巨大モデル前提のアイデアは当日スコープから外す。
- 生成AIの必然性を毎回言語化する。無くても成立するなら別案を優先。

## メモ / 未決事項
- ハッカソンが「沖縄開催 or 沖縄テーマ」なら ID-17 / ID-01 の地域性が加点されうる
- チーム戦なら ID-31 を共通基盤にして複数機能を分担する構成も可
- SNS を使う案（ID-22 等）は「誰でも同条件で取り直せるか（再現性）」を要検討。X API は不使用、Bluesky で設計
- ID-17 の波浪データは気象庁の公開範囲で1年分そろうか要確認（ダメなら波を外す）
