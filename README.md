# 🎮 game-news-crawler

매일 아침, 게임 산업 데이터 사이트의 **새 글을 자동으로 수집해 브리핑**으로 만드는 파이프라인.
GitHub Actions cron으로 돌기 때문에 **내 PC가 꺼져 있어도** 매일 실행된다.

## 무엇을 하나

1. **수집(collect)** — SensorTower 블로그에서 최신 글의 제목·링크·날짜를 긁는다.
2. **검증(validate)** — 개수/필수필드/중복을 점검해 PASS·REDO 판정 (REDO면 재수집, 최대 2회).
3. **변경 감지(state)** — 지난번 최신 글과 같으면 **브리핑을 건너뛴다** (낭비 방지).
4. **브리핑(notify)** — 새 글이 있으면 `briefing.md`를 만든다.

결과물(`briefing.md`)과 상태(`_state/last_seen.json`)는 매 실행마다 repo에 커밋되어,
**git 이력만 봐도 "언제 새 글이 올라왔는지" 추적**할 수 있다.

## 실행

```bash
pip install -r requirements.txt
python pipeline.py            # 정상 실행
python pipeline.py --inject   # 결함 주입 → 검증 루프(REDO) 관찰
```

## 자동 실행 (클라우드)

`.github/workflows/daily.yml` — 매일 **00:00 UTC (한국시간 09:00)** 자동 실행.
GitHub 저장소의 **Actions 탭 → Run workflow** 로 수동 실행도 가능.

## 구조

| 파일 | 역할 |
|------|------|
| `collect.py` | 크롤링 + 구조화 (소스 추가는 `SOURCES` 튜플에) |
| `validate.py` | 데이터 품질 검증 (PASS/REDO) |
| `state.py` | 변경 감지 (최신 글 시그니처 비교) |
| `notify.py` | 브리핑 마크다운 생성 |
| `pipeline.py` | 위 단계를 잇는 오케스트레이터 |

## 크롤링 원칙

- robots.txt 허용 + 서버렌더링 사이트만 대상으로 한다.
- Cloudflare 등 봇 차단이 있는 사이트(예: Newzoo)는 자동 크롤링에서 제외한다.

---
게임 PM 지망 학습용 포트폴리오 프로젝트.
