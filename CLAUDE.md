# game-news-crawler

게임 산업 뉴스를 매일 자동 수집·검증해 `briefing.md`로 남기는 파이프라인.
GitHub Actions cron으로 09:00 KST(00:00 UTC)에 실행되며, 결과물을 repo에 되커밋한다.

## 구조

```
pipeline.py       오케스트레이터: collect → validate 루프 → 변경감지 → briefing
collect.py        수집(author 역할). SOURCES 튜플에 소스 함수를 등록한다.
validate.py       검증(reviewer 역할). PASS/REDO 판정. 순수 함수.
state.py          변경 감지. 소스별 최신 글 URL 시그니처를 비교/저장. 순수 함수.
steam_metrics.py  Steam Web API에서 동시 접속자 수 수집. collect.py의 기사 파이프라인과 분리.
notify.py         briefing.md 생성.
```

데이터 흐름(기사): `collect()` → `list[dict]` (`{title, url, date, source}`) → `validate()` → `has_changed()` → `notify()` → `save_last_seen()`

데이터 흐름(Steam 지표): `steam.collect_players()` → `list[dict]` (`{appid, game, players, timestamp}`) → `notify()`가 별도 섹션으로만 병합.
**validate/state를 거치지 않는다** — 기사처럼 "새 글 여부"를 판단할 대상이 아니라 매번 갱신되는 실시간 스냅샷이라, 기사 브리핑을 새로 쓸 때만 같이 수집한다(pipeline.py 참고). 한 게임의 API 응답이 실패해도 나머지는 계속 수집한다(`collect.safe()`와 동일한 격리 원칙).

`date`는 소스 표기 그대로의 문자열(예: `"Gaming Insights • July 2026"`)이며 파싱하지 않는다.
`_state/last_seen.json`은 `{"<source>": "<최신글 url>"}` 형태다.

## 실행

```bash
python pipeline.py            # 정상 흐름
python pipeline.py --inject   # 첫 수집에 결함 주입 → REDO 경로 관찰용
```

## 설계 제약 (변경 시 주의)

- **`_workspace/`는 휘발성**이라 gitignore 대상. **`briefing.md`와 `_state/last_seen.json`은 의도적으로 커밋**한다 — Actions 러너는 실행이 끝나면 파일이 사라지므로, 상태를 repo에 남겨야 다음 실행이 변경을 감지할 수 있다.
- `collect.safe()`는 한 소스가 실패해도 나머지를 살리기 위해 예외를 삼킨다. 이 격리는 의도된 것이지만, **최종 실패까지 조용해지면 안 된다.**
- `validate`는 판정이 불확실하면 PASS가 아니라 REDO 쪽으로 기운다.
- `collect_newzoo()`는 Cloudflare 봇 차단으로 `SOURCES`에서 제외돼 있다. 재활용 목적으로 함수만 보존 — 삭제하지 말 것.
- 크롤링 대상은 robots 허용 + 서버렌더링을 확인한 곳만 추가한다.
- `steam_metrics.py`가 쓰는 `ISteamUserStats/GetNumberOfCurrentPlayers`는 스크래핑이 아니라 공식 API라 robots 원칙과 무관하다. 단, 스팀은 다운로드 수/판매량 자체를 공개하지 않으므로 "동시 접속자 수"를 대안 지표로 쓰고 있다는 점을 잊지 말 것 — 다운로드 수와 동일시해서 브리핑에 쓰면 안 된다.
- `steam_metrics.WATCHLIST`는 고정 목록(소수 게임)이다. 감시 대상을 동적으로(예: 그날 수집된 기사에서 언급된 게임) 넓히려면 별도 설계가 필요 — 지금은 범위 밖.

## 테스트

```bash
pip install -r requirements-dev.txt
pytest                                     # 58개
pytest --cov=collect --cov=logconf --cov=notify --cov=pipeline --cov=state --cov=validate --cov=steam_metrics --cov-report=term-missing
```

앱 코드 커버리지 88%. 남은 미커버는 각 모듈의 `main()`(CLI 래퍼)뿐이다.
`--cov=.`로 돌리면 테스트 파일까지 세서 수치가 부풀려진다 — 위 명령을 쓸 것.

## 남은 과제

- `logconf.setup()` 본문과 각 `main()`은 테스트 미커버.

## 규칙

이 프로젝트는 ECC 규칙을 따른다. `.claude/rules/ecc/common/`(공통) + `.claude/rules/ecc/python/`(파이썬).
특히 `testing.md`(pytest, 커버리지 80%), `coding-style.md`(PEP 8, 타입 어노테이션), `python/hooks.md`(`print` 대신 `logging`).

`README.md`는 사람 대상 소개 문서이고, 이 파일은 에이전트 대상 제약 문서다. 역할을 섞지 말 것.
