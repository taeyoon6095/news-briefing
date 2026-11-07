import argparse
import json
import re
import shutil
import sys
from datetime import datetime
from html import escape
from pathlib import Path

from common import DATE_RE, ROOT, korean_date, load_config, resolve, site_base

ICONS = {
    "paper": '<path d="M4 5h13v14H6a2 2 0 0 1-2-2V5Z"/><path d="M17 9h3v8a2 2 0 0 1-2 2"/><path d="M7 9h7M7 12h7M7 15h4"/>',
    "chart": '<path d="M4 19h16"/><path d="M6 15l4-4 3 3 5-6"/><path d="M15 8h3v3"/>',
    "people": '<circle cx="9" cy="8" r="3"/><path d="M3 19c0-3.3 2.7-5 6-5s6 1.7 6 5"/><circle cx="17" cy="9" r="2.3"/><path d="M16 14c2.8 0 5 1.4 5 4.5"/>',
    "chip": '<rect x="7" y="7" width="10" height="10" rx="1.5"/><path d="M10 3v4M14 3v4M10 17v4M14 17v4M3 10h4M3 14h4M17 10h4M17 14h4"/>',
    "globe": '<circle cx="12" cy="12" r="8.5"/><path d="M3.5 12h17M12 3.5c2.4 2.4 3.5 5.3 3.5 8.5s-1.1 6.1-3.5 8.5c-2.4-2.4-3.5-5.3-3.5-8.5S9.6 5.9 12 3.5Z"/>',
}
def icon(name: str) -> str:
    return ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" '
            f'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{ICONS.get(name, ICONS["paper"])}</svg>')


def day_class(date: str) -> str:
    wd = datetime.strptime(date, "%Y-%m-%d").weekday()
    return {5: "sat", 6: "sun"}.get(wd, "")


def fill(template: str, values: dict) -> str:
    out = template
    for key, value in values.items():
        out = out.replace("{{" + key + "}}", value)
    left = re.findall(r"\{\{[A-Z_]+\}\}", out)
    if left:
        raise SystemExit(f"템플릿 값 누락: {left}")
    return out


def sources_html(sources: list) -> str:
    return "".join(
        f'<a href="{escape(s["url"], quote=True)}" target="_blank" rel="noopener noreferrer">'
        f'{escape(s["name"])} 원문</a>'
        for s in sources
    )


def render_page(data: dict, cfg: dict, base: str) -> str:
    meta = {s["name"]: s for s in cfg["sections"]}
    date = data["date"]
    top = data["top_story"]
    top_meta = meta.get(top["section"], cfg["sections"][0])

    headlines = "\n".join(f"    <li>{escape(line)}</li>" for line in data["headline_summary"])

    blocks = []
    for sec in data["sections"]:
        m = meta.get(sec["name"], {"color": "slate", "icon": "paper"})
        items = "\n".join(
            f'    <div class="item"><h3>{escape(it["title"])}</h3><p>{escape(it["summary"])}</p>'
            f'<div class="src">{sources_html(it["sources"])}</div></div>'
            for it in sec["items"]
        )
        blocks.append(
            f'  <section class="sec c-{m["color"]}">\n'
            f'    <h2><span class="tag">{icon(m["icon"])}{escape(sec["name"])}</span></h2>\n'
            f"{items}\n  </section>"
        )

    template = (ROOT / "templates" / "page.html").read_text(encoding="utf-8")
    return fill(template, {
        "TITLE": escape(cfg["title"]),
        "DATE": date,
        "DATE_KO": escape(korean_date(date)),
        "DAY": str(int(date[-2:])),
        "DAY_CLASS": day_class(date),
        "HEADLINES": headlines,
        "TOP_COLOR": top_meta["color"],
        "TOP_ICON": icon(top_meta["icon"]),
        "TOP_SECTION": escape(top["section"]),
        "TOP_TITLE": escape(top["title"]),
        "TOP_SUMMARY": escape(top["summary"]),
        "TOP_SOURCES": sources_html(top["sources"]),
        "SECTIONS": "\n\n".join(blocks),
        "BASE": escape(base, quote=True),
    })


def render_archive(out_root: Path, cfg: dict, base: str, extra: dict) -> str:
    dates = sorted((p.name for p in out_root.iterdir() if p.is_dir() and DATE_RE.match(p.name)), reverse=True)
    rows = []
    for d in dates:
        data = extra.get(d)
        if data is None:
            jp = ROOT / "briefings" / f"{d}.json"
            data = json.loads(jp.read_text(encoding="utf-8")) if jp.exists() else {}
        first = (data.get("headline_summary") or [""])[0]
        rows.append(
            f'    <li><a href="{escape(base, quote=True)}/{d}/">'
            f'<span class="d {day_class(d)}">{int(d[-2:])}</span>'
            f'<span><span class="when">{escape(korean_date(d))}</span>'
            f'<span class="what">{escape(first)}</span></span></a></li>'
        )
    if not rows:
        rows.append('    <li class="empty">아직 발행된 호가 없습니다.</li>')
    template = (ROOT / "templates" / "archive.html").read_text(encoding="utf-8")
    return fill(template, {"TITLE": escape(cfg["title"]), "ISSUES": "\n".join(rows), "BASE": escape(base, quote=True)})


def main() -> int:
    ap = argparse.ArgumentParser(description="브리핑 JSON으로 신문 페이지 생성")
    ap.add_argument("date", nargs="?", default="today", help="YYYY-MM-DD | today | sample")
    ap.add_argument("--dry-run", action="store_true", help="docs/ 대신 out/site-preview/에 생성")
    args = ap.parse_args()

    date, json_path = resolve(args.date)
    cfg = load_config()
    data = json.loads(json_path.read_text(encoding="utf-8"))

    if args.dry_run:
        out_root = ROOT / "out" / "site-preview"
        if out_root.exists():
            shutil.rmtree(out_root)
        out_root.mkdir(parents=True)
        base = out_root.resolve().as_uri()
    else:
        out_root = ROOT / "docs"
        out_root.mkdir(exist_ok=True)
        base = site_base()

    page = render_page(data, cfg, base)
    day_dir = out_root / date
    day_dir.mkdir(exist_ok=True)
    (day_dir / "index.html").write_text(page, encoding="utf-8")

    latest = max(p.name for p in out_root.iterdir() if p.is_dir() and DATE_RE.match(p.name))
    if latest == date:
        (out_root / "index.html").write_text(page, encoding="utf-8")
    (out_root / "archive.html").write_text(render_archive(out_root, cfg, base, {date: data}), encoding="utf-8")
    (out_root / ".nojekyll").touch()

    where = out_root.relative_to(ROOT)
    print(f"[build_site] {where}/{date}/index.html 생성 (최신 호: {latest})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
