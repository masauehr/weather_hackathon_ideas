"""ID-32 検証: 気象庁の天気図・衛星赤外・アメダス実況・予報概況を取得する。

出力（data/<基準時刻>/ 配下。git 除外）:
  surface_asia.png   アジア太平洋 地上天気図（ASAS）
  surface_near.png   日本近海 地上天気図（着色）
  ir_japan.png       ひまわり赤外（B13）全球画像から日本周辺(z=4, 2x2タイル)を結合
  amedas.json        主要地点のアメダス実況（気温・風・降水）
  overview.json      府県予報の概況テキスト
  meta.json          取得元URLと時刻
出典: 気象庁ホームページ
"""
import io
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

import requests
from PIL import Image

BASE = "https://www.jma.go.jp/bosai"
UA = {"User-Agent": "weather-hackathon-spike (personal research)"}
DATA = Path(__file__).parent / "data"

# 実況の裏取りに使う主要地点（アメダス地点コード）
STATIONS = {
    "札幌": "14163", "新潟": "54232", "金沢": "56227", "東京": "44132",
    "名古屋": "51106", "大阪": "62078", "福岡": "82182", "那覇": "91197",
}
# 予報概況を取る府県予報区
OFFICES = {"東京都": "130000", "新潟県": "150000", "石川県": "170000", "北海道(石狩)": "016000"}


def get(url, **kw):
    r = requests.get(url, headers=UA, timeout=30, **kw)
    r.raise_for_status()
    return r


def latest_chart(kind):
    """list.json の now 配列の末尾（最新）を返す。"""
    files = get(f"{BASE}/weather_map/data/list.json").json()[kind]["now"]
    return files[-1]


def chart_valid_utc(name):
    """天気図ファイル名から対象時刻(UTC, 14桁)を取り出す。"""
    return name.split("_")[6]


def fetch_ir(out, target_utc):
    """ひまわり赤外 B13 を全球(fd)の z=4 2x2 タイル(x=13,14 / y=5,6 ≒ 東経112〜157度・北緯22〜55度)で結合する。

    jp 域は斜めに欠けた範囲しかなく太平洋側が空白になるため fd を使う。
    """
    times = get(f"{BASE}/himawari/data/satimg/targetTimes_fd.json").json()
    # 天気図の対象時刻に最も近い観測を選ぶ（時刻ずれで解説と実況が食い違うのを防ぐ）
    t = min(times, key=lambda x: abs(int(x["validtime"]) - int(target_utc)))
    base, valid = t["basetime"], t["validtime"]
    canvas = Image.new("RGB", (512, 512))
    for yi, y in enumerate((5, 6)):
        for xi, x in enumerate((13, 14)):
            url = f"{BASE}/himawari/data/satimg/{base}/fd/{valid}/B13/TBB/4/{x}/{y}.jpg"
            canvas.paste(Image.open(io.BytesIO(get(url).content)).convert("RGB"), (xi * 256, yi * 256))
    canvas.save(out)
    return {"basetime": base, "validtime": valid}


def fetch_amedas(target_utc):
    """天気図の対象時刻(UTC→JST)のアメダス全国マップから主要地点を抜き出す。"""
    jst = datetime.strptime(target_utc, "%Y%m%d%H%M%S") + timedelta(hours=9)
    stamp = jst.strftime("%Y%m%d%H%M%S")
    m = get(f"{BASE}/amedas/data/map/{stamp}.json").json()
    keys = ("temp", "wind", "windDirection", "precipitation1h", "precipitation10m", "humidity", "pressure", "normalPressure")
    out = {}
    for name, code in STATIONS.items():
        rec = m.get(code, {})
        # 値は [値, 品質フラグ] の形式
        out[name] = {k: rec[k][0] for k in keys if k in rec and rec[k]}
    return stamp, out


def main():
    DATA.mkdir(exist_ok=True)
    asia, near = latest_chart("asia"), latest_chart("near")
    # 日本近海天気図(near)の対象時刻(UTC)に衛星・アメダスを揃える。アジア図は 6 時間毎のため直近を併記
    base_utc = chart_valid_utc(near)
    out = DATA / base_utc
    out.mkdir(exist_ok=True)
    meta = {"asia": asia, "near": near}
    (out / "surface_asia.png").write_bytes(get(f"{BASE}/weather_map/data/png/{asia}").content)
    (out / "surface_near.png").write_bytes(get(f"{BASE}/weather_map/data/png/{near}").content)
    meta["ir"] = fetch_ir(out / "ir_japan.png", base_utc)
    stamp, amedas = fetch_amedas(base_utc)
    meta["amedas_time"] = stamp
    (out / "amedas.json").write_text(json.dumps(amedas, ensure_ascii=False, indent=2))
    overview = {}
    for name, code in OFFICES.items():
        try:
            overview[name] = get(f"{BASE}/forecast/data/overview_forecast/{code}.json").json()
        except Exception as e:  # noqa: BLE001 取得失敗は記録して続行
            overview[name] = {"error": str(e)}
    (out / "overview.json").write_text(json.dumps(overview, ensure_ascii=False, indent=2))
    (out / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2))
    print(out)
    print(json.dumps(meta, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    sys.exit(main())
