import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KST = timezone(timedelta(hours=9))
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
WEEKDAYS = "월화수목금토일"


def today_kst() -> str:
    return datetime.now(KST).strftime("%Y-%m-%d")


def load_config() -> dict:
    return json.loads((ROOT / "config" / "briefing.json").read_text(encoding="utf-8"))


def resolve(arg: str | None) -> tuple[str, Path, Path]:
    if arg in (None, "", "today"):
        arg = today_kst()
    if arg == "sample":
        json_path = ROOT / "briefings" / "sample.json"
        script_path = ROOT / "briefings" / "sample.script.txt"
        date = json.loads(json_path.read_text(encoding="utf-8"))["date"]
        return date, json_path, script_path
    if not DATE_RE.match(arg):
        raise SystemExit(f"날짜 형식 오류: {arg} (YYYY-MM-DD, today, sample 중 하나)")
    return arg, ROOT / "briefings" / f"{arg}.json", ROOT / "briefings" / f"{arg}.script.txt"


def audio_path(date: str) -> Path:
    return ROOT / "out" / f"{date}.mp3"


def korean_date(date: str) -> str:
    d = datetime.strptime(date, "%Y-%m-%d")
    return f"{d.year}년 {d.month}월 {d.day}일 ({WEEKDAYS[d.weekday()]})"


def site_base(dry_run: bool = False) -> str:
    base = os.environ.get("SITE_BASE_URL", "").rstrip("/")
    if not base and not dry_run:
        raise SystemExit("SITE_BASE_URL 환경 변수가 없습니다")
    return base


def require_env(name: str) -> str:
    value = os.environ.get(name, "")
    if not value:
        raise SystemExit(f"{name} 환경 변수가 없습니다")
    return value


def mask(text: str) -> str:
    for name in ("TELEGRAM_BOT_TOKEN", "GOOGLE_TTS_API_KEY", "TELEGRAM_CHAT_ID"):
        value = os.environ.get(name)
        if value:
            text = text.replace(value, f"<{name}>")
    return text
