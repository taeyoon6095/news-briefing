# news-briefing

매일 아침 Claude Code 루틴이 뉴스를 모아 모바일 신문 페이지(GitHub Pages)를 만들고, 3줄 요약과 페이지 링크를 텔레그램 가족방에 보냅니다. 서버 없이 Anthropic 클라우드에서만 돌고, 집 컴퓨터는 꺼 둬도 됩니다.

## 따라 하는 사람이 바꿀 값

| 바꿀 곳 | 내용 |
|---|---|
| 저장소 이름 | `news-briefing` (다르게 하면 `SITE_BASE_URL`도 맞춘다) |
| `config/briefing.json` | `title`(신문 이름), `sections`(분야와 기사 수) |
| 루틴 환경 변수 | 아래 표 4개 |
| 루틴 일정 | 발송 시각 15분 전 |

## 1. 저장소와 Pages

1. 이 폴더를 **공개** 저장소 `news-briefing`으로 올린다
2. Settings → Pages → Source: `Deploy from a branch`, Branch: `main` / `/docs`
3. 주소(`https://아이디.github.io/news-briefing`)를 `SITE_BASE_URL`로 쓴다

## 2. 텔레그램

1. BotFather에서 `/newbot`으로 봇을 만들고 토큰을 받는다
2. 개인 chat ID: 봇에게 아무 메시지나 보낸 뒤 `https://api.telegram.org/bot<토큰>/getUpdates`를 브라우저로 열어 `chat.id` 확인
3. 가족방 chat ID: 봇을 가족방에 초대하고 방에 메시지를 하나 보낸 뒤 다시 getUpdates 확인. 그룹 ID는 `-100`으로 시작하는 음수
4. 처음에는 개인 chat ID로 시험하고, 잘 되면 가족방 ID로 바꾼다

## 3. 루틴 환경

환경 변수 (값은 저장소에 절대 넣지 않는다):

| 이름 | 내용 |
|---|---|
| `TZ` | `Asia/Seoul` |
| `TELEGRAM_BOT_TOKEN` | 봇 토큰 |
| `TELEGRAM_CHAT_ID` | 시험 중엔 개인 ID, 이후 가족방 ID |
| `SITE_BASE_URL` | `https://아이디.github.io/news-briefing` (끝에 `/` 없이) |

네트워크 허용 목록:

- `api.telegram.org`
- `아이디.github.io` (페이지 반영 확인용)
- `pypi.org`, `files.pythonhosted.org`

브랜치: 루틴이 `main`에 직접 푸시할 수 있도록 설정한다. 기본값이 `claude/` 브랜치만 허용이면 Pages가 갱신되지 않는다.

루틴 만들기: `ROUTINE_PROMPT.md` 참고.

## 4. 로컬 리허설

```bash
bash scripts/run_daily.sh --dry-run sample
```

키 없이 검사 → `out/site-preview/`에 페이지 생성 → 전송 메시지 미리보기까지 돈다.

## 구조

```
CLAUDE.md                    루틴이 매번 읽는 규칙 요약
.claude/skills/news-briefing 수집·편집 규칙
.claude/agents/              section-reporter(수집), editor(검수)
config/briefing.json         신문 이름, 분야
templates/                   신문 지면, 지난 호 템플릿
scripts/                     validate, build_site, wait_page, send_telegram, run_daily.sh
briefings/                   날짜별 JSON (영구 보관)
docs/                        GitHub Pages 공개 폴더 (build_site.py가 생성)
out/                         미리보기 (커밋하지 않음)
```
