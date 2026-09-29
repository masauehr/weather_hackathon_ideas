"""GenAI角（ID-35「生成シナリオの説明・妥当性チェックのレポート」）の実証。

validate.py が出した機械的なチェック結果（数値のみ）を、Claude（テキストのみ・画像なし）に
渡して「このシナリオはどう解釈できるか・どこまで信用できるか」を平文で説明させる。
LLMには数値の再計算をさせず、渡した数値の解釈・要約のみをさせる（数値のハルシネーション対策）。

使い方:
  python explain_report.py --pressure 900   観測範囲内寄りの強い台風
  python explain_report.py --pressure 820   観測範囲外（史上最低870hPaを下回る）の合成シナリオ
"""
import argparse
import json
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[3]  # weather_hackathon_ideas/
load_dotenv(ROOT_DIR / ".env")

import anthropic

MODEL = "claude-sonnet-5"

BASE_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = BASE_DIR / "results"

SYSTEM_PROMPT = """あなたは気象データサイエンティストです。台風の強度合成シナリオ生成
（条件付きVAEで「もっと強い台風」の中心気圧の経過を合成する試み）について、機械的な
検証結果（数値のみ）が与えられます。これを読んで、一般の防災担当者にも分かる平文で
「このシナリオは何を意味するか」「どこまで信用できるか」を説明してください。

厳守事項:
- 与えられた数値を書き換えない・新しい数値を計算しない（解釈・要約のみ）。
- 生成された台風が「実際に発生する」という断定はしない。あくまで統計モデルによる合成である旨を明記する。
- 外挿（観測範囲外の条件）の結果は、観測範囲内の結果より信頼性が低いことを明示する。
- 出力は日本語のプレーンテキスト（見出しと箇条書き程度は可、JSON化しない）。300字程度で簡潔に。"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pressure", type=float, default=900.0,
                         help="説明したい合成シナリオの目標最低気圧(hPa)")
    args = parser.parse_args()

    validation = json.loads((OUT_DIR / "validation_report.json").read_text())
    target = args.pressure
    following = [f for f in validation["条件追従性（合成条件と実際の生成結果のズレ）"]
                 if abs(f["target_hpa"] - target) < 1]
    row = following[0] if following else min(
        validation["条件追従性（合成条件と実際の生成結果のズレ）"],
        key=lambda f: abs(f["target_hpa"] - target),
    )

    user_text = (
        f"合成条件: 最低気圧 {target}hPa を指定。\n"
        f"実際の生成結果: 平均 {row['actual_mean_hpa']}hPa（ズレ {row['gap_hpa']}hPa）。\n"
        f"観測データ全体の最低気圧: {validation['観測データの最低気圧']}hPa。\n"
        f"気圧-風速の物理的整合性: {json.dumps(validation['気圧-風速の物理的整合性'], ensure_ascii=False)}\n"
        f"機械的な結論: {validation['結論']}\n\n"
        f"この情報から、このシナリオ（目標{target}hPa）の解釈と信頼性を説明してください。"
    )

    client = anthropic.Anthropic()
    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        output_config={"effort": "low"},
        messages=[{"role": "user", "content": user_text}],
    )
    text = next((b.text for b in response.content if b.type == "text"), None)
    if text is None:
        print("エラー: text ブロックがありません。stop_reason=", response.stop_reason)
        return 1

    print(text)
    cost = response.usage.input_tokens * 2 / 1e6 + response.usage.output_tokens * 10 / 1e6
    print(f"\n---\n概算コスト: ${cost:.4f}")

    out_path = OUT_DIR / f"explain_{int(target)}hpa.txt"
    out_path.write_text(text)
    print(f"保存先: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
