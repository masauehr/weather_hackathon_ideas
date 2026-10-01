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

### 🎯 実装した案（設計 → 実装まで進んだもの）

| 案 | 内容 | 実装 |
|---|---|---|
| [ID-32](docs/idea_catalog.md) 天気図VLM解説 | 天気図・衛星画像をVLMで読み、気圧配置を判定して平文解説＋読み方教材 | 独立プロジェクト [weather_chart_vlm](https://github.com/masauehr/weather_chart_vlm)（[デモ](https://masauehr.github.io/weather_chart_vlm/webui/index.html)）として実装・公開済み。設計の経緯は[docs/candidates/c32_weather_chart_vlm.md](docs/candidates/c32_weather_chart_vlm.md) |
| [ID-15](docs/idea_catalog.md) 濡れない経路 | 高解像度降水ナウキャストで自転車/徒歩の経路上の降雨有無を判定し、出発時刻を提案 | 独立プロジェクト [dry_route](https://github.com/masauehr/dry_route)（[デモ](https://dry-route.onrender.com)）として実装・公開済み |
| [ID-22](docs/idea_catalog.md) SNS災害情報×気象実況のクロスチェック | SNS投稿の位置推定・地図プロット・公式情報との整合チェックで「確認済み/未確認/要注意」の信頼度ラベルを付与 | 別プロジェクトとして実装済み（自分用途のため非公開・本リポジトリからのリンクなし） |
| [ID-25](docs/idea_catalog.md) 生鮮野菜価格の気象先行指標 | 産地（前橋）の真夏日数 → 東京の葉物卸売価格・入荷量の先行性を統計的に検証（相関の当たり付けが目的、Web/生成AI部分は未実装） | 本リポジトリ内 [experiments/cs07_veg_price/](experiments/cs07_veg_price/) で検証済み。真夏日+10日→翌月価格+約10%（p=0.001）だが、月次2値の早期警戒アラートとしては弱い（AUC≈0.55）。結果まとめ: [SPINACH_FINDINGS.md](experiments/cs07_veg_price/SPINACH_FINDINGS.md) |
| [ID-35](docs/idea_catalog.md) 極端気象の合成データ生成 | 気象庁ベストトラック（台風の中心気圧時系列）を条件付きVAEで学習し、「もっと強い台風」の合成データ生成＋妥当性チェック＋Claudeによる平文説明レポートまで実装 | 本リポジトリ内 [experiments/id35_synthetic_typhoon/](experiments/id35_synthetic_typhoon/README.md) で検証済み。観測範囲内は追従するが、観測史上最低(870hPa)を大きく下回る条件はこの構成では指定通りに生成できない（一部GO） |
| [ID-01](docs/idea_catalog.md) 再エネ出力予測＋需給ナレーション | 太陽光の出力制御（カーテイルメント）が天気・曜日で説明できるかを九州・沖縄の実際の出力制御実績で比較＋ロジスティック回帰＋GenAI角（天気予報→平文説明） | 本リポジトリ内 [experiments/id01_curtailment_compare/](experiments/id01_curtailment_compare/README.md) で検証済み。**九州は制御日の日照時間が非制御日の約1.6倍（曜日統制後も差が残る）と強い相関**のため九州エリアを推奨。ロジスティック回帰でROC-AUC 0.669、**天気予報→予測→Claudeの平文説明のGenAIパイプラインも実証済み（GO）** |

検討のみで検証・実装を見送った案（[docs/candidates/](docs/candidates/) に詳細設計を残す）:

| 案 | ドキュメント | 一言 |
|---|---|---|
| ID-17 | [docs/candidates/c17_beach_day_planner.md](docs/candidates/c17_beach_day_planner.md) | 天気・風・潮位・UVから「海日和スコア」＋半日プラン生成（沖縄の海） |
| ID-05 | [docs/candidates/c05_meteoropathy_assistant.md](docs/candidates/c05_meteoropathy_assistant.md) | 気圧変化からリスク指数を予測し、理由説明とセルフケアを対話提供 |

比較: [docs/candidates/README.md](docs/candidates/README.md)（3案の48h開発視点の比較・絞り込み手順。ID-32を選定した経緯）

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
- **ID-32 天気図VLM解説のAPI実証＋複数事例の正答率測定を実施（2026-09-28）**: `vlm_read.py`（当日1事例、実況・予報つき、NG0件・$0.018/回）と `fetch_hibiten.py`＋`eval_historical.py`（気象庁「日々の天気図」アーカイブから過去15事例・7パターンを抽出し正答率測定）を追加。**結果: 15事例中10件正解（67%）、コスト$0.065**。台風・梅雨前線・移動性高気圧は強い一方、「日本海低気圧」を「南岸低気圧」と系統的に誤答する弱点を発見。
- **ID-32を独立プロジェクトとして切り出し（2026-09-29）**: 検証GOだったため [weather_chart_vlm](https://github.com/masauehr/weather_chart_vlm)（[デモ](https://masauehr.github.io/weather_chart_vlm/webui/index.html)、毎朝8:45 JST・Macのlaunchdで自動更新。2026-10-01にGitHub Actionsのschedule遅延・欠落のため6:13 JSTから移行）として独立。本リポジトリの`experiments/cs32_chart_vlm/`・GitHub Pages・GitHub Actionsは停止済み。設計の経緯は[docs/candidates/c32_weather_chart_vlm.md](docs/candidates/c32_weather_chart_vlm.md)に残す。
- **ID-17/ID-05の検証は見送り、暫定でID-32（天気図VLM解説）に絞る（2026-09-28）**: 実際に検証まで済んだのがID-32のみのため（[docs/evaluation.md](docs/evaluation.md)）。要項判明後に審査基準と照らして再確認する前提。
- **ID-15「濡れない経路」を検証・独立プロジェクトとして切り出し（2026-09-29）**: 高解像度降水ナウキャストのタイル（αチャンネル）で降雨有無を機械的に判定できることを実測で確認、奄美市名瀬の実データ（帯状のレーダーエコー接近中）で出発時刻をずらす効果を確認（20分後だけ40%濡れ、他は0%）。OSRMで道路にスナップした経路・Webアプリも実装し、GOだったため [dry_route](https://github.com/masauehr/dry_route)（[デモ](https://dry-route.onrender.com)、Render無料プラン）として独立。本リポジトリの`experiments/id15_dry_route/`は削除済み。
- **ID-22「SNS災害情報×気象実況のクロスチェック」を別プロジェクトとして実装済み（2026-09-29確認）**: SNS投稿の収集・位置推定（精度A〜D）・地図プロット・元投稿へのリンク・公式情報（気象庁）との整合チェックによるフェイク自動判定（確認済み/未確認/要注意＋根拠）まで実装済み。**自分用途のため非公開**、本リポジトリからはリンクしない（[docs/existing_assets.md](docs/existing_assets.md)の「公開リポジトリのみ」方針に合わせる）。
- **ID-35「極端気象の合成データ生成」をスパイクで検証（2026-09-29）**: 台風の強度（中心気圧）で検証。気象庁ベストトラック（1951年〜・1959台風）を条件付きVAEで学習し、生成・妥当性チェック（条件追従性／気圧-風速の物理的整合性・r≈0.97）・Claudeによる平文の説明レポート（$0.006〜0.007/回）まで一通り実装。**一部GO**: 観測範囲内は誤差数hPaで追従するが、観測史上最低(870hPa)を大きく下回る「もっと強い台風」はこの単純なCVAE構成では指定通りに生成できない（外挿にバイアスがかかる）。詳細は [experiments/id35_synthetic_typhoon/](experiments/id35_synthetic_typhoon/README.md)。
- **ID-01「再エネ出力予測＋需給ナレーション」を出力制御の角度でスパイク検証（2026-09-30）**: 単純な日射量×太陽光実績（テスト2）より実用性が高い角度として、太陽光の出力制御（カーテイルメント）が天気・曜日で説明できるかを九州電力送配電・沖縄電力（沖縄本島）の実際の出力制御実績（九州Excel1175日分/沖縄PDF160日分）で比較。**九州は制御日の日照時間が非制御日の約1.6倍（曜日を統制しても差が残る、日曜のみでも6.66h vs 3.41h）と強い相関、沖縄は曜日を統制すると相関が消える（5.03h vs 5.06h）**。データ形式（九州=Excel/沖縄=PDF）・期間（九州8年/沖縄4年）も九州が優位のため**九州エリアを推奨（GO）**。詳細は [experiments/id01_curtailment_compare/](experiments/id01_curtailment_compare/README.md)。
- **ID-01の追加検証: 「日照時間＋曜日（土日祝）」のロジスティック回帰で制御有無を予測（2026-10-01）**: 九州で時系列分割（前70%学習・後30%評価）のロジスティック回帰を実施。**ROC-AUC 0.669**（天気・曜日単独より両方使う方が上がる＝相補的）。評価期間は太陽光導入量増加で制御日の割合が学習期間より大幅に高く、この分布シフトのせいでトレンド項（経過年数）が無いと確率を過小評価し再現率0.339止まり、トレンド項を1つ加えるだけで再現率0.882まで改善（AUCは不変）。詳細は [experiments/id01_curtailment_compare/](experiments/id01_curtailment_compare/README.md#追加検証-ロジスティック回帰でどこまで予測できるか九州)。
- **ID-01のGenAI角を実証: 翌日予報→ロジスティック回帰→Claudeの平文説明（2026-10-01）**: 翌日の日照時間予報 → 上記ロジスティック回帰で出力制御確率を予測 → Claude（$0.004〜0.005/回）が数値を解釈して事業者向けの平文説明を生成、という一連のパイプラインが実際に動作することを確認。ID-01が狙っていた「GenAIの必然性」を小規模に実証。詳細は [experiments/id01_curtailment_compare/](experiments/id01_curtailment_compare/README.md#追加検証-genai角天気予報からの平文説明id-01のgenai角そのもの)。
- **農研機構AMGSDS数値予報との比較で簡略化の過大評価を発見（2026-10-01）**: 気象庁の天気カテゴリ（晴れ/曇り）を実測日照時間の分位点で代用する簡略化は、農研機構メッシュ農業気象データ（AMGSDS、気象庁モデル由来の派生データ。[CLAUDE.md](CLAUDE.md)で第三者APIとして例外許可）の実際の数値予報と比べて**日照時間を約2倍過大評価**していた（簡略化9.1h vs AMGSDS実測4.57h、出力制御予測確率0.823 vs 0.636）。GenAI角のパイプラインをAMGSDS優先（簡略化はフォールバックのみ）に修正。AMGSDSはメッシュ（面）データのため、単一地点だけでなく九州本土全体（陸上セル37,731点）の分布も取得できることを確認。詳細は [experiments/id01_curtailment_compare/](experiments/id01_curtailment_compare/README.md#追加検証2-農研機構amgsds数値予報との比較簡略化は過大評価だった)。
- 次: 3分デモ筋書きを [docs/candidates/c32_weather_chart_vlm.md](docs/candidates/c32_weather_chart_vlm.md) をもとに詰める → ハッカソン要項の確認（[plan.md](plan.md) フェーズ4）。

## 🛠️ 実装メモ

- Python環境: `met_env` 相当（Python 3.11、pandas / scipy / statsmodels / matplotlib / beautifulsoup4）。ルートに [requirements.txt](requirements.txt)。
- 検証コードは `experiments/<テーマ>/`、生データ・出力図の一部は `data/`（git 除外）。結果図・集計は各テーマの `results/`（git 追跡）。
- 気象庁API・各データの利用規約を遵守。図表には「気象庁ホームページ」等の出典を明記。詳細は [CLAUDE.md](CLAUDE.md)
