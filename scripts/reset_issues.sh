#!/usr/bin/env bash
# 저장소를 복사해 새로 시작할 때, 원래 주인의 지난 호를 지운다.
# 사용법: bash scripts/reset_issues.sh
set -euo pipefail
cd "$(dirname "$0")/.."

rm -rf docs/20[0-9][0-9]-*/
rm -f docs/index.html docs/archive.html
find briefings -name '20[0-9][0-9]-*.json' -delete
touch docs/.nojekyll

echo "지난 호를 지웠습니다. 남은 파일:"
ls docs briefings
