# 루틴 프롬프트

claude.ai/code/routines에서 루틴을 만들 때 아래 블록을 그대로 붙여 넣는다.

```
오늘 날짜(KST)의 아침 뉴스 브리핑을 만들어 발송해. 날짜는 반드시 `TZ=Asia/Seoul date +%F`로 구한다.

1. CLAUDE.md와 news-briefing 스킬 규칙을 따른다.
2. config/briefing.json의 분야마다 section-reporter 서브에이전트를 병렬로 실행해 기사 후보를 모은다. 각 서브에이전트에 분야 이름과 오늘 날짜를 함께 준다.
3. 후보를 합쳐 briefings/오늘날짜.json을 작성한다.
4. editor 서브에이전트로 검수하고 지적 사항을 반영한다. 출처 URL이 열리지 않는 기사는 빼거나 다른 출처로 바꾼다.
5. scripts/run_daily.sh 오늘날짜 를 실행한다.
6. FAILED_STEP이 나오면 python3 scripts/send_telegram.py 오늘날짜 --fail "단계이름" 을 실행하고 끝낸다.
7. 마지막에 발송 결과를 한 줄로 남긴다: 기사 수, 페이지 링크.
```

## 루틴 설정값

| 항목 | 값 |
|---|---|
| 이름 | 아침 뉴스 브리핑 |
| 저장소 | taeyoon6095/news-briefing |
| 트리거 | 일정, 매일 06:45 (KST), 발송 시각 15분 전 |
| 환경 | README의 환경 변수와 네트워크 허용 목록 |
| 브랜치 | main에 직접 푸시 허용 |
| 커넥터 | 없음 |
