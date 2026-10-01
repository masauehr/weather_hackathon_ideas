#!/bin/bash
# 都営バスの遅延を定期ポーリングするラッパースクリプト（launchdから起動）。
# ODPTには履歴アーカイブが無いため、これを定期実行して自分でログを溜める。
set -euo pipefail

PROJECT_DIR="/Users/masahiro/projects/weather_hackathon_ideas/experiments/id37_bus_delay_weather"
PYTHON="/opt/anaconda3/envs/met_env/bin/python"

cd "$PROJECT_DIR/src"
echo "=== $(date '+%Y-%m-%d %H:%M:%S') ==="
"$PYTHON" poll_bus_delay.py
