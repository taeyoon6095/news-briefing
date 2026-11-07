import argparse
import sys
import time
import urllib.request

from common import load_config, resolve, site_base


def main() -> int:
    ap = argparse.ArgumentParser(description="GitHub Pages에 오늘 지면이 반영될 때까지 대기")
    ap.add_argument("date", nargs="?", default="today")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    date, _ = resolve(args.date)
    timeout = load_config()["site"]["page_wait_timeout_sec"]
    if args.dry_run:
        print(f"[wait_page] dry-run: 실제 실행 시 {date} 지면을 최대 {timeout}초 기다림")
        return 0

    url = f"{site_base()}/{date}/"
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            req = urllib.request.Request(url, headers={"Cache-Control": "no-cache"})
            with urllib.request.urlopen(req, timeout=15) as r:
                if r.status == 200 and date in r.read().decode("utf-8", "ignore"):
                    print(f"[wait_page] 반영 확인: {url}")
                    return 0
        except Exception:
            pass
        time.sleep(15)
    print(f"[wait_page] {timeout}초 안에 페이지가 반영되지 않음: {url}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
