import argparse
import json
import sys
import time
from html import escape

from common import audio_path, korean_date, load_config, mask, require_env, resolve, site_base, today_kst

API = "https://api.telegram.org/bot{token}/{method}"


def call(session, token: str, method: str, retries: int, **kwargs) -> dict:
    last = ""
    for attempt in range(1, retries + 1):
        try:
            r = session.post(API.format(token=token, method=method), timeout=120, **kwargs)
            body = r.json()
        except Exception as e:
            last = type(e).__name__
        else:
            if body.get("ok"):
                return body
            last = f"HTTP {r.status_code} {mask(str(body.get('description', '')))[:200]}"
            if r.status_code == 400:
                break
            wait = body.get("parameters", {}).get("retry_after")
            if wait:
                time.sleep(min(int(wait), 30))
                continue
        time.sleep(3 * attempt)
    raise RuntimeError(f"{method} 실패: {last}")


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
    cfg = load_config()
    tg = cfg["telegram"]

    if args.fail:
        date = today_kst() if args.date in (None, "today", "sample") else args.date
        text = f"오늘 브리핑 생성 실패 ({escape(date)})\n실패 단계: {escape(args.fail)}"
        if args.dry_run:
            print(f"[telegram] dry-run 실패 알림:\n{text}")
            return 0
        import requests
        with requests.Session() as s:
            call(s, require_env("TELEGRAM_BOT_TOKEN"), "sendMessage", tg["retries"],
                 data={"chat_id": require_env("TELEGRAM_CHAT_ID"), "text": text})
        print("[telegram] 실패 알림 전송")
        return 0

    date, json_path, _ = resolve(args.date)
    data = json.loads(json_path.read_text(encoding="utf-8"))
    base = site_base(args.dry_run) or "https://example.github.io/news-briefing"
    url = f"{base}/{date}/"
    message = build_message(data, url)
    mp3 = audio_path(date)
    title = f"{date} {tg['audio_title_suffix']}"

    if args.dry_run:
        state = "있음" if mp3.exists() else "없음 (dry-run이면 정상)"
        print(f"[telegram] dry-run 메시지:\n{message}\n[telegram] 음성: {mp3.name} {state}, 제목 \"{title}\"")
        return 0

    if not mp3.exists():
        raise RuntimeError(f"음성 파일 없음: {mp3.name}")

    import requests

    token, chat = require_env("TELEGRAM_BOT_TOKEN"), require_env("TELEGRAM_CHAT_ID")
    with requests.Session() as s:
        call(s, token, "sendMessage", tg["retries"], data={
            "chat_id": chat, "text": message, "parse_mode": "HTML", "disable_web_page_preview": "false",
        })
        duration = int(float(data.get("audio", {}).get("duration_sec") or 0))
        with mp3.open("rb") as f:
            call(s, token, "sendAudio", tg["retries"],
                 data={"chat_id": chat, "title": title, "performer": tg["performer"], "duration": duration},
                 files={"audio": (mp3.name, f, "audio/mpeg")})
    print(f"[telegram] 전송 완료: 메시지 + {mp3.name}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except RuntimeError as e:
        print(f"[telegram] {e}")
        sys.exit(1)
