# news-briefing

매일 아침 뉴스를 모아 모바일 신문 페이지(GitHub Pages)와 10분 이내 아나운서 음성(mp3)을 만들어 텔레그램 가족방에 보낸다. 실행은 Claude Code 루틴(클라우드)에서만 한다.

## 하루 실행 순서
1. 날짜는 항상 KST 기준 (`TZ=Asia/Seoul`). 컨테이너 기본 시간대는 UTC다.
2. `news-briefing` 스킬 규칙대로 분야별 `section-reporter`로 기사 후보 수집
3. `briefings/YYYY-MM-DD.json`, `briefings/YYYY-MM-DD.script.txt` 작성
4. `editor`로 검수 (출처 URL 실제 확인 포함) 후 반영
5. `scripts/run_daily.sh YYYY-MM-DD` 실행: validate → tts → build_site → push → 페이지 반영 대기 → telegram
6. tts 종료 코드 2(10분 초과)면 원고를 줄이고 5를 다시 (최대 2회)

## 금지 사항
- 기사 문장·제목을 그대로 옮기지 않는다. 요약은 직접 쓰고 근거는 링크로만
- 언론사 사진, 로고, 그래픽 사용 금지
- 키, 토큰, chat ID를 파일에 쓰거나 로그에 출력하지 않는다 (공개 저장소)
- mp3는 저장소에 커밋하지 않는다. 음성은 텔레그램으로만 보낸다 (`out/`은 gitignore)
- `docs/` 안의 HTML은 손으로 고치지 말고 `build_site.py`로만 만든다
