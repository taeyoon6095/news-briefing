import argparse
import base64
import json
import re
import shutil
import subprocess
import sys
import time

from common import audio_path, load_config, mask, require_env, resolve

API = "https://texttospeech.googleapis.com/v1/text:synthesize"
EXIT_TOO_LONG = 2


def split_chunks(text: str, max_bytes: int) -> list[str]:
    sentences: list[str] = []
    for para in re.split(r"\n\s*\n", text.strip()):
        para = " ".join(para.split())
        sentences += [s for s in re.split(r"(?<=[.!?])\s+", para) if s]
        if sentences:
            sentences[-1] += "\n"

    chunks: list[str] = []
    current = ""
    for s in sentences:
        while len(s.encode("utf-8")) > max_bytes:
            cut = max_bytes // 3
            head, s = s[:cut], s[cut:]
            if current:
                chunks.append(current.strip())
                current = ""
            chunks.append(head.strip())
        candidate = f"{current} {s}" if current else s
        if len(candidate.encode("utf-8")) > max_bytes:
            chunks.append(current.strip())
            current = s
        else:
            current = candidate
    if current.strip():
        chunks.append(current.strip())
    return chunks


def synthesize(session, key: str, text: str, tts_cfg: dict) -> bytes:
    body = {
        "input": {"text": text},
        "voice": {"languageCode": tts_cfg["language_code"], "name": tts_cfg["voice"]},
        "audioConfig": {"audioEncoding": "MP3", "speakingRate": tts_cfg["speaking_rate"], "sampleRateHertz": 24000},
    }
    last = ""
    for attempt in range(1, 4):
        try:
            r = session.post(API, json=body, headers={"X-Goog-Api-Key": key}, timeout=60)
        except Exception as e:
            last = type(e).__name__
        else:
            if r.status_code == 200:
                return base64.b64decode(r.json()["audioContent"])
            try:
                msg = r.json().get("error", {}).get("message", "")
            except ValueError:
                msg = ""
            last = f"HTTP {r.status_code} {mask(msg)[:200]}"
            if r.status_code < 500 and r.status_code != 429:
                break
        time.sleep(2 * attempt)
    raise RuntimeError(f"TTS 요청 실패: {last}")


def strip_id3(data: bytes) -> bytes:
    if data[:3] == b"ID3" and len(data) > 10:
        size = (data[6] << 21) | (data[7] << 14) | (data[8] << 7) | data[9]
        return data[10 + size:]
    return data


def measure(path) -> float:
    try:
        from mutagen.mp3 import MP3
        return float(MP3(path).info.length)
    except ImportError:
        pass
    if shutil.which("ffprobe"):
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
            capture_output=True, text=True,
        ).stdout.strip()
        if out:
            return float(out)
    return path.stat().st_size * 8 / 32000


def main() -> int:
    ap = argparse.ArgumentParser(description="아나운서 원고를 mp3로 변환")
    ap.add_argument("date", nargs="?", default="today", help="YYYY-MM-DD | today | sample")
    ap.add_argument("--dry-run", action="store_true", help="API 호출 없이 분할과 예상 길이만 출력")
    args = ap.parse_args()

    date, json_path, script_path = resolve(args.date)
    cfg = load_config()
    tts_cfg, max_sec = cfg["tts"], cfg["limits"]["max_duration_sec"]
    text = script_path.read_text(encoding="utf-8")
    chunks = split_chunks(text, tts_cfg["max_request_bytes"])
    sizes = ", ".join(str(len(c.encode("utf-8"))) for c in chunks)

    if args.dry_run:
        chars = len(text.strip())
        est = chars / tts_cfg["chars_per_minute"] * 60
        print(f"[tts] dry-run {date}: {chars}자, {len(chunks)}조각 ({sizes} 바이트), 예상 {est:.0f}초 / 상한 {max_sec}초")
        return EXIT_TOO_LONG if est > max_sec else 0

    import requests

    key = require_env("GOOGLE_TTS_API_KEY")
    out = audio_path(date)
    out.parent.mkdir(exist_ok=True)
    with requests.Session() as session:
        parts = []
        for i, chunk in enumerate(chunks):
            audio = synthesize(session, key, chunk, tts_cfg)
            parts.append(audio if i == 0 else strip_id3(audio))
    out.write_bytes(b"".join(parts))

    duration = round(measure(out), 1)
    data = json.loads(json_path.read_text(encoding="utf-8"))
    data.setdefault("audio", {})["duration_sec"] = duration
    json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    rate = len(text.strip()) / (duration / 60) if duration else 0
    print(f"[tts] {out.name} {duration:.0f}초 ({len(chunks)}조각, 실측 분당 {rate:.0f}자)")
    if duration > max_sec:
        print(f"[tts] 재생 시간 {duration:.0f}초가 상한 {max_sec}초를 넘었습니다. 원고를 줄이세요.")
        return EXIT_TOO_LONG
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except RuntimeError as e:
        print(f"[tts] {e}")
        sys.exit(1)
