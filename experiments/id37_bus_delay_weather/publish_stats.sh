#!/bin/bash
# stats.jsonを再生成し、変化があればGitHubにpushする（GitHub Pagesの監視ページ用）。
# launchdから30分おきに起動する想定。生データ(data/)はpushせず、集計結果のみ公開する。
set -euo pipefail

REPO_DIR="/Users/masahiro/projects/weather_hackathon_ideas"
PROJECT_DIR="$REPO_DIR/experiments/id37_bus_delay_weather"
PYTHON="/opt/anaconda3/envs/met_env/bin/python"

cd "$PROJECT_DIR/src"
echo "=== $(date '+%Y-%m-%d %H:%M:%S') ==="
"$PYTHON" gen_stats.py

cd "$REPO_DIR"
if ! git diff --quiet -- experiments/id37_bus_delay_weather/docs/stats.json; then
    git add experiments/id37_bus_delay_weather/docs/stats.json
    git commit -m "chore(id37): stats.json自動更新 ($(date '+%Y-%m-%d %H:%M'))

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
    git push
    echo "push完了"
else
    echo "変化なし、pushスキップ"
fi
