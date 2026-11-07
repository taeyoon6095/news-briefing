import argparse
import json
import re
import sys
from datetime import datetime
from urllib.parse import urlparse

from common import DATE_RE, load_config, resolve

EMOJI_RE = re.compile("[\U0001F000-\U0001FAFF☀-➿⬀-⯿️]")
FORBIDDEN = {
    "URL": re.compile(r"https?://|www\.", re.I),
    "괄호": re.compile(r"[()\[\]{}（）「」『』<>]"),
    "목록 기호": re.compile(r"^\s*([-*•·▶■□●○]|\d+[.)])\s", re.M),
    "마크다운": re.compile(r"[#*_`|]"),
}
CLOSING = "지금까지 아침 브리핑이었습니다."


def check_url(url: str) -> bool:
    try:
        p = urlparse(url)
    except ValueError:
        return False
    return p.scheme in ("http", "https") and "." in p.netloc and " " not in url


def check_sources(where: str, sources, errors: list[str]) -> None:
    if not isinstance(sources, list) or not sources:
        errors.append(f"{where}: sources가 비어 있음")
        return
    for i, s in enumerate(sources, 1):
        if not isinstance(s, dict) or not str(s.get("name", "")).strip():
            errors.append(f"{where} 출처 {i}: name 없음")
        if not check_url(str(s.get("url", "")) if isinstance(s, dict) else ""):
            errors.append(f"{where} 출처 {i}: URL 형식 오류")


def check_item(where: str, item, errors: list[str], top: bool = False) -> None:
    if not isinstance(item, dict):
        errors.append(f"{where}: 객체가 아님")
        return
    for key in ("title", "summary"):
        if not str(item.get(key, "")).strip():
            errors.append(f"{where}: {key} 없음")
    if len(str(item.get("title", ""))) > 40:
        errors.append(f"{where}: 제목이 40자를 넘음")
    check_sources(where, item.get("sources"), errors)


def validate_json(data: dict, date: str, cfg: dict) -> list[str]:
    errors: list[str] = []
    names = [s["name"] for s in cfg["sections"]]

    if data.get("date") != date:
        errors.append(f"date 불일치: {data.get('date')} (기대값 {date})")
    if not DATE_RE.match(str(data.get("date", ""))):
        errors.append("date 형식 오류")
    try:
        datetime.fromisoformat(str(data.get("generated_at", "")))
    except ValueError:
        errors.append("generated_at 형식 오류 (ISO 8601)")

    lines = data.get("headline_summary")
    n = cfg["limits"]["headline_lines"]
    if not isinstance(lines, list) or len(lines) != n or not all(str(x).strip() for x in lines):
        errors.append(f"headline_summary는 비어 있지 않은 {n}줄이어야 함")

    top = data.get("top_story")
    if not isinstance(top, dict):
        errors.append("top_story 없음")
    else:
        check_item("top_story", top, errors, top=True)
        if top.get("section") not in names:
            errors.append(f"top_story.section 값 오류: {top.get('section')}")

    sections = data.get("sections")
    if not isinstance(sections, list) or not sections:
        errors.append("sections 없음")
        sections = []
    seen_urls: dict[str, str] = {}
    for si, sec in enumerate(sections, 1):
        name = sec.get("name") if isinstance(sec, dict) else None
        if name not in names:
            errors.append(f"sections {si}: 분야 값 오류 {name}")
        items = sec.get("items") if isinstance(sec, dict) else None
        if not isinstance(items, list) or not items:
            errors.append(f"{name}: items 없음")
            continue
        for ii, item in enumerate(items, 1):
            where = f"{name} {ii}번"
            check_item(where, item, errors)
            for s in item.get("sources", []) if isinstance(item, dict) else []:
                url = s.get("url") if isinstance(s, dict) else None
                if url and url in seen_urls:
                    errors.append(f"{where}: 같은 출처 URL이 {seen_urls[url]}에도 있음 (중복 기사 의심)")
                elif url:
                    seen_urls[url] = where

    audio = data.get("audio", {})
    if not isinstance(audio, dict) or not isinstance(audio.get("duration_sec", 0), (int, float)):
        errors.append("audio.duration_sec는 숫자여야 함")
    return errors


def validate_script(text: str, date: str, cfg: dict) -> list[str]:
    errors: list[str] = []
    limit = cfg["limits"]["max_script_chars"]
    length = len(text.strip())
    if length == 0:
        return ["원고가 비어 있음"]
    if length > limit:
        errors.append(f"원고 {length}자, 상한 {limit}자 초과")
    d = datetime.strptime(date, "%Y-%m-%d")
    opening = f"안녕하십니까, {d.month}월 {d.day}일 아침 뉴스 브리핑입니다."
    if not text.strip().startswith(opening):
        errors.append(f"오프닝 문구 불일치 (기대: {opening})")
    if not text.strip().endswith(CLOSING):
        errors.append(f"클로징 문구 불일치 (기대: {CLOSING})")
    for label, pattern in FORBIDDEN.items():
        m = pattern.search(text)
        if m:
            errors.append(f"원고에 {label} 사용: {m.group(0).strip()!r}")
    if EMOJI_RE.search(text):
        errors.append("원고에 이모지 사용")
    return errors


def main() -> int:
    ap = argparse.ArgumentParser(description="브리핑 JSON과 원고 검사")
    ap.add_argument("date", nargs="?", default="today", help="YYYY-MM-DD | today | sample")
    ap.add_argument("--dry-run", action="store_true", help="검사만 하므로 동작은 같음")
    args = ap.parse_args()

    date, json_path, script_path = resolve(args.date)
    cfg = load_config()
    errors: list[str] = []

    if not json_path.exists():
        errors.append(f"파일 없음: {json_path.name}")
    else:
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
            errors += validate_json(data, date, cfg)
        except json.JSONDecodeError as e:
            errors.append(f"JSON 문법 오류: {e}")

    if not script_path.exists():
        errors.append(f"파일 없음: {script_path.name}")
    else:
        errors += validate_script(script_path.read_text(encoding="utf-8"), date, cfg)

    if errors:
        print(f"[validate] 실패 {len(errors)}건")
        for e in errors:
            print(f"  - {e}")
        return 1
    print(f"[validate] 통과 {date}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
