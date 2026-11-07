#!/usr/bin/env bash
# 사용법: scripts/run_daily.sh [--dry-run] [YYYY-MM-DD | today | sample]
# 종료 코드: 0 성공, 1 실패(FAILED_STEP 출력), 2 음성 10분 초과
set -uo pipefail
export TZ=Asia/Seoul

DRY=""
DATE="today"
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY="--dry-run" ;;
    *) DATE="$arg" ;;
  esac
done

cd "$(dirname "$0")/.."
PY="${PYTHON:-python3}"

fail() {
  echo "FAILED_STEP=$1"
  exit "${2:-1}"
}

step() {
  local name="$1"; shift
  echo "== $name"
  "$@"
}

if [ -z "$DRY" ]; then
  step "패키지 확인" $PY -c "import requests, mutagen" 2>/dev/null \
    || step "패키지 설치" $PY -m pip install -q -r requirements.txt || fail "패키지 설치"
fi

[ "$DATE" = "today" ] && DATE="$(date +%F)"
echo "== 날짜 $DATE (KST) ${DRY:+[dry-run]}"

step "validate" $PY scripts/validate.py "$DATE" || fail validate

step "tts" $PY scripts/tts.py $DRY "$DATE"
rc=$?
if [ $rc -eq 2 ]; then fail tts-too-long 2; fi
[ $rc -eq 0 ] || fail tts

step "build_site" $PY scripts/build_site.py $DRY "$DATE" || fail build_site

if [ -z "$DRY" ]; then
  if [ "$DATE" = "sample" ]; then
    echo "샘플 데이터는 게시하지 않습니다. --dry-run으로 실행하세요."
    exit 1
  fi
  echo "== git push"
  git add docs "briefings/$DATE.json" "briefings/$DATE.script.txt" || fail git-add
  git commit -q -m "brief: $DATE" || echo "(변경 없음)"
  git push -q origin HEAD:main || fail git-push
fi

step "wait_page" $PY scripts/wait_page.py $DRY "$DATE" || fail wait_page
step "telegram" $PY scripts/send_telegram.py $DRY "$DATE" || fail telegram

echo "== 완료 $DATE"
