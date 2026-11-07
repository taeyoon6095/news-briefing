import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from html import escape

from common import korean_date, load_config, mask, require_env, resolve, site_base, today_kst

API = "https://api.telegram.org/bot{token}/{method}"


def post(url: str, payload: dict) -> tuple[int, dict]:
    data = urllib.parse.urlencode(payload).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except ValueError:
            return e.code, {}


def send(text: str, html: bool, retries: int) -> None:
    token, chat = require_env("TELEGRAM_BOT_TOKEN"), require_env("TELEGRAM_CHAT_ID")
    payload = {"chat_id": chat, "text": text}
    if html:
        payload["parse_mode"] = "HTML"
    url = API.format(token=token, method="sendMessage")
    last = ""
    for attempt in range(1, retries + 1):
        try:
            status, body = post(url, payload)
        except Exception as e:
            last = type(e).__name__
        else:
            if body.get("ok"):
                return
            last = f"HTTP {status} {mask(str(body.get('description', '')))[:200]}"
            if status == 400:
                break
            wait = body.get("parameters", {}).get("retry_after")
            if wait:
                time.sleep(min(int(wait), 30))
                continue
        time.sleep(3 * attempt)
    raise RuntimeError(f"sendMessage 실패: {last}")


def build_message(data: dict, url: str) -> str:
    lines = [f"<b>{escape(korean_date(data['date']))} 아침 브리핑</b>", ""]
    lines += [f"{i}. {escape(s)}" for i, s in enumerate(data["headline_summary"], 1)]
    lines += ["", f'<a href="{escape(url, quote=True)}">오늘 신문 펼쳐 보기</a>']
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="텔레그램으로 브리핑 전송")
    ap.add_argument("date", nargs="?", default="today", help="YYYY-MM-DD | today | sample")
    ap.add_argument("--dry-run", action="store_true", help="보내지 않고 메시지만 출력")
    ap.add_argument("--fail", metavar="단계", help="실패 알림만 보내기")
    args = ap.parse_args()
    retries = load_config()["telegram"]["retries"]

    if args.fail:
        date = today_kst() if args.date in (None, "today", "sample") else args.date
        text = f"오늘 브리핑 생성 실패 ({date})\n실패 단계: {args.fail}"
        if args.dry_run:
            print(f"[telegram] dry-run 실패 알림:\n{text}")
            return 0
        send(text, html=False, retries=retries)
        print("[telegram] 실패 알림 전송")
        return 0

    date, json_path = resolve(args.date)
    data = json.loads(json_path.read_text(encoding="utf-8"))
    base = site_base(args.dry_run) or "https://example.github.io/news-briefing"
    message = build_message(data, f"{base}/{date}/")

    if args.dry_run:
        print(f"[telegram] dry-run 메시지:\n{message}")
        return 0

    send(message, html=True, retries=retries)
    print("[telegram] 전송 완료")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except RuntimeError as e:
        print(f"[telegram] {e}")
        sys.exit(1)
