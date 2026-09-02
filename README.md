# weather_hackathon_ideas

気象データ × 各種データの相関分析・機械学習予測モデル・生成AI活用の**アイデア出し**を行うプロジェクト。
「気象 × 生成AI ハッカソン」の事前準備を兼ねる。案を広く集めて評価・選抜する段階（一部は [experiments/](experiments/) で相関の当たり付けまで実施済み）。

> このREADMEが**目次（ハブ）**です。各ドキュメントの冒頭にもREADMEへ戻るリンクがあります。

> 🔑 **データ利用の絶対ルール**（[CLAUDE.md](CLAUDE.md)）: 気象データは**気象庁HPから取得**（過去 = [obsdl](https://www.data.jma.go.jp/risk/obsdl/index.php)、実況・予報 = bosai、天気図・衛星 = 気象庁画像）。相手側は**誰でも同じ手順でアクセスできる公開データのみ**。個人データ・非公開データ（自宅の電力使用量、自分のGPSログ等）は使わない。GRIB（数値予報GPV）は容量のため扱わない。

## 目的

1. 気象データと他分野データ（電力・健康・農業・交通・小売・防災・経済など）の**相関仮説**を洗い出す
2. その相関を使った**機械学習予測モデル**の案を列挙する
3. 予測結果や気象情報に**生成AI（LLM / VLM）を組み合わせる体験設計**を考える
4. ハッカソンで実際に作る 1〜3 案に**絞り込む**ための評価軸を用意する

## 📑 ドキュメント一覧

| ドキュメント | 内容 | 主な見出し |
|---|---|---|
| 📋 [plan.md](plan.md) | 次の一手・準備タスク・確定要項欄 | 確定要項 / フェーズ1〜5 |
| 💡 [docs/idea_catalog.md](docs/idea_catalog.md) | アイデア一覧（`ID-01`〜`ID-36` ＋種）。**主成果物** | A:電力 / B:健康 / C:農業 / D:交通 / E:小売・観光 / F:防災 / G:経済・行政 / H:環境 / I:スポーツ・行動 / J:基盤 |
| 🗄️ [docs/data_sources.md](docs/data_sources.md) | 使えるデータソース棚卸し（気象庁＋公開データのみ） | 気象（すべて気象庁） / 相手側データ / 生成AI・モデル / 事前準備 |
| 🔗 [docs/correlation_studies.md](docs/correlation_studies.md) | 「まず相関を確認する」小規模検証 `CS-01`〜`CS-10` | 各CSの仮説・最小データ・手法・GO基準 |
| ⚡ [docs/data_easy_tests.md](docs/data_easy_tests.md) | **データ取得が容易な順**の相関テスト候補3件（1年分以上・GRIB除外） | テスト1:気温×電力需要 / テスト2:日射×太陽光実績 / テスト3:気温・絶対湿度×インフル |
| 🤖 [docs/ml_models.md](docs/ml_models.md) | 予測モデル設計 `MM-01`〜`MM-08` | 目的変数 / 特徴量 / 手法 / 検証 / 落とし穴 |
| ✨ [docs/genai_angles.md](docs/genai_angles.md) | 生成AIの絡ませ方 `GA-01`〜`GA-08` | パターン別 / アイデア対応表 / ガードレール |
| ⚖️ [docs/evaluation.md](docs/evaluation.md) | 評価軸と候補スコアリング | 6軸 / 暫定スコア表 / 第一次候補 / 絞り込み手順 |
| 🧰 [docs/existing_assets.md](docs/existing_assets.md) | ~/projects 内の流用可能な既存資産 | 気象取得 / 電力 / 生成AI / 台風 / 経済・家計 |
| 🎯 [docs/candidates/](docs/candidates/) | 第一次候補の詳細設計（下表） | — |
| 🧪 [experiments/](experiments/) | 相関の当たり付けスパイク（実コード）。生データは `data/`（git除外） | [cs07_veg_price](experiments/cs07_veg_price/)（ID-25 生鮮野菜価格の気象先行指標） |

### 🎯 第一次候補（詳細設計）

| 案 | ドキュメント | 一言 | 元アイデア |
|---|---|---|---|
| ID-32 | [docs/candidates/c32_weather_chart_vlm.md](docs/candidates/c32_weather_chart_vlm.md) | 天気図・衛星をVLMで読み、気圧配置を判定して平文解説＋読み方教材 | [idea_catalog ID-32](docs/idea_catalog.md) |
| ID-17 | [docs/candidates/c17_beach_day_planner.md](docs/candidates/c17_beach_day_planner.md) | 天気・風・潮位・UVから「海日和スコア」＋半日プラン生成（沖縄の海） | [idea_catalog ID-17](docs/idea_catalog.md) |
| ID-05 | [docs/candidates/c05_meteoropathy_assistant.md](docs/candidates/c05_meteoropathy_assistant.md) | 気圧変化からリスク指数を予測し、理由説明とセルフケアを対話提供 | [idea_catalog ID-05](docs/idea_catalog.md) |
| 比較 | [docs/candidates/README.md](docs/candidates/README.md) | 3案の48h開発視点の比較・絞り込み手順 | — |

## 🔄 進め方

```
アイデア発散(idea_catalog)  →  相関の当たり付け(correlation_studies)
        ↓
生成AI体験の設計(genai_angles)  →  評価・選抜(evaluation)  →  候補の詳細設計(candidates)
        ↓
ハッカソン当日: 選抜した 1 案をプロトタイピング
```

- ドキュメント間の依存関係:
  - [idea_catalog](docs/idea_catalog.md) が起点。各アイデアが [data_sources](docs/data_sources.md) / [genai_angles](docs/genai_angles.md) を参照
  - [correlation_studies](docs/correlation_studies.md) と [ml_models](docs/ml_models.md) は「GO したら次へ」の関係
  - [evaluation](docs/evaluation.md) が候補を選び、[candidates](docs/candidates/) で深掘り
  - [existing_assets](docs/existing_assets.md) は全ドキュメントから参照される流用マップ

## 📌 状態

- 2026-09-02 新規作成。アイデア発散フェーズ。
- 第一次候補3案の詳細設計まで完了（[docs/candidates/](docs/candidates/)）。
- データ利用ルールを確定（気象庁のみ・公開データのみ・個人データ不可・GRIB不使用）。全ドキュメントに反映済み。
- データ取得が容易な順の相関テスト3件を [docs/data_easy_tests.md](docs/data_easy_tests.md) に整理。
- **相関スパイクを1件実施（[experiments/cs07_veg_price/](experiments/cs07_veg_price/)、ID-25 / CS-07）**:
  「産地（前橋）の真夏日数 → 東京のほうれんそう卸売価格・入荷量」を月次15年（2011〜2026）で検証。
  分布ラグ回帰（交絡統制・HAC）で **真夏日+10日 → 翌月の卸売価格 +約10%／入荷量 −15%**（ラグ1か月 β=+0.0096, t=+3.3, p=0.001）。
  「気象単独で価格を当てる」ことはできない（予測R²の上乗せ小）が、**早期警戒シグナルとして有効**。結果まとめ → [SPINACH_FINDINGS.md](experiments/cs07_veg_price/SPINACH_FINDINGS.md)。
  副産物: 気象庁 etrn ＋ ベジ探（東京都中央卸売市場データ）の完全自動取得コード。
- 次: ハッカソン要項の確認 → 評価軸の重み付け → 1案に絞る（[plan.md](plan.md) フェーズ4）。

## 🛠️ 実装メモ

- Python環境: `met_env` 相当（Python 3.11、pandas / scipy / statsmodels / matplotlib / beautifulsoup4）。ルートに [requirements.txt](requirements.txt)。
- 検証コードは `experiments/<テーマ>/`、生データ・出力図の一部は `data/`（git 除外）。結果図・集計は各テーマの `results/`（git 追跡）。
- 気象庁API・各データの利用規約を遵守。図表には「気象庁ホームページ」等の出典を明記。詳細は [CLAUDE.md](CLAUDE.md)
