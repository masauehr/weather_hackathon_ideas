# CLAUDE.md — weather_hackathon_ideas

## このプロジェクトの位置づけ
気象 × 生成AI ハッカソンの事前準備。アイデア出し・データ調査・評価が目的。
**現時点ではコード実装しない。** MDファイルの整理・追記が主な作業。

## 作業ルール
- ドキュメントは日本語。Markdown。
- アイデアには必ず ID（`ID-NN`）を振り、分野タグを付ける。
- データソースを挙げるときは「入手性 / ライセンス / 時間・空間粒度 / 遅延」を必ず書く。
- 「生成AIの必然性」を各アイデアで明示する（LLMが無くても成立するなら、その旨も書く）。
- 既存 ~/projects 資産の流用可能性を [docs/existing_assets.md](docs/existing_assets.md) に随時追記。

## 実装フェーズに移ったら
- Python は `met_env` 相当の環境を想定。まず `requirements.txt` を作る。
- 検証コードは `experiments/` に置く。データは `data/`（git 除外）。
- 気象庁API・各データの利用規約を遵守。

## ハッカソン要項が判明したら
[plan.md](plan.md) の冒頭に「確定要項」節を作り、日程・テーマ・利用可能API・審査基準を転記。
評価軸（[docs/evaluation.md](docs/evaluation.md)）を要項に合わせて更新する。

## ドキュメント更新ルール（親CLAUDE.md準拠）
このプロジェクトに実質的な変更を加えたら `pc_docs/manuals/automation/`（またはハッカソン成果物に応じた場所）へ反映し、
`pc_docs/README.md` のテーブルも更新する。現段階（アイデアのみ）では対象外。
