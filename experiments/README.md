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
| [cs07_veg_price/](cs07_veg_price/) | [ID-25](../docs/idea_catalog.md) / [CS-07](../docs/correlation_studies.md) | 産地の日照不足 → 数週後の葉物卸売価格 の先行性 | 着手（プランビング作成） |
