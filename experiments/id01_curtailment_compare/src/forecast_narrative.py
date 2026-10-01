"""ID-01のGenAI角そのもの: 翌日の日照時間予報から
「明日は出力制御の可能性が高い/低い」を平文で説明するレポートを生成する（次にやるなら②の実施）。

パイプライン:
1. 日照時間の予報値を取得する。優先順位:
   a. 農研機構メッシュ農業気象データ（AMGSDS）の数値予報（SSD、福岡単一点）
      ※ CLAUDE.mdで例外的に使用を許可した第三者API。気象庁カテゴリ予報より定量的で精度が高い
         ことを実測で確認済み（compare_naro_forecast.py参照、簡略化9.1h vs AMGSDS実測4.57h）。
   b. AMGSDSが使えない場合（API障害・トークン失効等）のフォールバックとして、気象庁 bosai の
      短期予報JSON（福岡県 400000）の天気カテゴリ（晴れ/曇り/雨系）を実測の日照時間分布の
      分位点に置き換える簡略化を使う（精度はAMGSDSより劣ることが分かっている）。
2. 明日が土日祝かどうかをjpholidayで判定
3. logistic_model.pyと同じ特徴量（日照時間＋曜日＋トレンド）でロジスティック回帰を学習し、
   明日の出力制御確率を予測
4. 予報値・出典・曜日・モデル確率（数値のみ）をClaude（テキストのみ）に渡し、
   一般向けの平文説明を生成させる（数値の再計算はさせず解釈のみ、ID-35のexplain_report.pyと同じ方針）
"""
import argparse
import datetime as dt
import json
import sys
from pathlib import Path

import jpholiday
import pandas as pd
import requests
from dotenv import load_dotenv
from sklearn.linear_model import LogisticRegression

from logistic_model import build_dataset

sys.path.insert(0, "/Users/masahiro/projects/common")

ROOT_DIR = Path(__file__).resolve().parents[3]  # weather_hackathon_ideas/
load_dotenv(ROOT_DIR / ".env")

import anthropic

MODEL = "claude-sonnet-5"
FORECAST_URL = "https://www.jma.go.jp/bosai/forecast/data/forecast/400000.json"
AREA_NAME = "福岡地方"
FUKUOKA_POINT = [33.6064, 33.6064, 130.4181, 130.4181]

BASE_DIR = Path(__file__).resolve().parent.parent
RESULTS_DIR = BASE_DIR / "results"

SYSTEM_PROMPT = """あなたは電力系統のデータアナリストです。翌日の日照時間予報と、太陽光の出力制御を
予測する統計モデルの結果（数値のみ）が与えられます。これを読んで、一般の太陽光発電事業者にも
わかる平文で「明日は出力制御の可能性が高いか低いか」を説明してください。

厳守事項:
- 与えられた数値を書き換えない・新しい数値を計算しない（解釈・要約のみ）。
- 日照時間の出典が「簡略化（天気カテゴリから代用）」の場合は、厳密な日射予測ではないことを明記する。
  出典が「農研機構AMGSDS（数値予報）」の場合は、気象庁モデル由来の定量予報である旨を伝えてよい。
- モデルの判別力（ROC-AUC 0.669、中程度）を踏まえ、断定的な言い方を避ける。
- 出力制御の有無を保証するものではない旨を明記する（最終判断は電力会社の公式発表による）。
- 出力は日本語のプレーンテキスト（見出しと箇条書き程度は可）。300字程度で簡潔に。"""


def fetch_tomorrow_forecast() -> dict:
    data = requests.get(FORECAST_URL, timeout=20).json()
    ts_weather = data[0]["timeSeries"][0]
    ts_pop = data[0]["timeSeries"][1]

    area_w = next(a for a in ts_weather["areas"] if a["area"]["name"] == AREA_NAME)
    area_p = next(a for a in ts_pop["areas"] if a["area"]["name"] == AREA_NAME)

    # timeDefines[1] が「明日」（[0]は今日）
    tomorrow_date = pd.Timestamp(ts_weather["timeDefines"][1]).date()
    weather_code = area_w["weatherCodes"][1]
    weather_text = area_w["weathers"][1]

    # pop(降水確率)は3時間毎。明日分（timeDefinesの日付が一致するもの）の平均を使う
    pops_tomorrow = [
        int(p) for t, p in zip(ts_pop["timeDefines"], area_p["pops"])
        if pd.Timestamp(t).date() == tomorrow_date and p
    ]
    pop_avg = sum(pops_tomorrow) / len(pops_tomorrow) if pops_tomorrow else None

    return {
        "date": tomorrow_date,
        "weather_code": weather_code,
        "weather_text": weather_text,
        "pop_avg": pop_avg,
    }


def weather_code_to_sunshine_proxy(weather_code: str, sunshine_quantiles: dict) -> tuple:
    """天気コードの先頭数字（1=晴れ系/2=曇り系/3,4=雨雪系）で、実測日照時間の分位点に置き換える
    （AMGSDSが使えないときのフォールバック）。返り値: (推定sunshine_h, カテゴリ名, 使った分位点)
    """
    first_digit = weather_code[0]
    if first_digit == "1":
        return sunshine_quantiles["q75"], "晴れ系", "75%ile"
    elif first_digit == "2":
        return sunshine_quantiles["q50"], "曇り系", "50%ile"
    else:
        return sunshine_quantiles["q10"], "雨/雪系", "10%ile"


def fetch_amgsds_sunshine(target_date: dt.date) -> float:
    """農研機構AMGSDSから指定日の日照時間(SSD)数値予報を福岡単一点で取得する。
    失敗時（API障害・トークン失効等）は例外を投げる（呼び出し側でフォールバックする）。
    """
    import AMD_Tools4_ue3 as amd
    today = dt.date.today().strftime("%Y-%m-%d")
    target_str = target_date.strftime("%Y-%m-%d")
    itsu = sorted({today, target_str})
    data, tim, _, _ = amd.GetMetData("SSD", itsu, FUKUOKA_POINT)
    idx = [pd.Timestamp(t).date() for t in tim].index(target_date)
    return float(data[idx, 0, 0])


def train_model(df: pd.DataFrame) -> LogisticRegression:
    features = ["sunshine_h", "is_weekend_or_holiday", "years_since_start"]
    model = LogisticRegression()
    model.fit(df[features], df["is_curtailed"])
    return model, features


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Claude APIを呼ばずモデル推定結果だけ表示")
    args = parser.parse_args()

    df = build_dataset()
    sunshine_quantiles = {
        "q75": df["sunshine_h"].quantile(0.75),
        "q50": df["sunshine_h"].quantile(0.50),
        "q10": df["sunshine_h"].quantile(0.10),
    }

    forecast = fetch_tomorrow_forecast()

    try:
        sunshine_h = fetch_amgsds_sunshine(forecast["date"])
        sunshine_source = "農研機構AMGSDS（数値予報、福岡単一点）"
    except Exception as e:
        sunshine_h, category, quantile_used = weather_code_to_sunshine_proxy(
            forecast["weather_code"], sunshine_quantiles)
        sunshine_source = f"簡略化（AMGSDS取得失敗: {e} → 天気カテゴリ「{category}」を実測の{quantile_used}で代用）"

    tomorrow_ts = pd.Timestamp(forecast["date"])
    is_weekend_or_holiday = int(
        tomorrow_ts.dayofweek in (5, 6) or jpholiday.is_holiday(forecast["date"]))
    years_since_start = (tomorrow_ts - df["date"].min()).days / 365.25

    model, features = train_model(df)
    x_tomorrow = pd.DataFrame([{
        "sunshine_h": sunshine_h,
        "is_weekend_or_holiday": is_weekend_or_holiday,
        "years_since_start": years_since_start,
    }])[features]
    proba = float(model.predict_proba(x_tomorrow)[0, 1])

    summary = {
        "対象日": str(forecast["date"]),
        "天気予報(気象庁)": forecast["weather_text"],
        "降水確率平均": forecast["pop_avg"],
        "日照時間の予報値": f"{sunshine_h:.2f}h",
        "日照時間の出典": sunshine_source,
        "土日祝か": bool(is_weekend_or_holiday),
        "モデルの出力制御確率": round(proba, 3),
        "モデルの判別力(参考)": "ROC-AUC 0.669（中程度の判別力、断定はできない）",
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    if args.dry_run:
        return 0

    client = anthropic.Anthropic()
    user_text = (
        f"明日（{summary['対象日']}）の福岡地方の天気予報: {summary['天気予報(気象庁)']}\n"
        f"降水確率平均: {summary['降水確率平均']}%\n"
        f"日照時間の予報値: {summary['日照時間の予報値']}\n"
        f"日照時間の出典: {summary['日照時間の出典']}\n"
        f"土日祝か: {summary['土日祝か']}\n"
        f"統計モデル（日照時間＋曜日＋経過年数のロジスティック回帰）による出力制御の予測確率: {summary['モデルの出力制御確率']}\n"
        f"モデルの判別力: {summary['モデルの判別力(参考)']}\n\n"
        "この情報から、明日の出力制御の可能性について説明してください。"
    )
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

    print("\n=== 生成されたレポート ===")
    print(text)
    cost = response.usage.input_tokens * 2 / 1e6 + response.usage.output_tokens * 10 / 1e6
    print(f"\n概算コスト: ${cost:.4f}")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = RESULTS_DIR / f"forecast_narrative_{forecast['date']}.txt"
    out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n\n" + text)
    print(f"保存先: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
