# notify (알림 단계): 검증 통과 데이터를 '게임 산업 브리핑' 문서로 남긴다.
# 실행(단독 테스트): repo 루트에서  python notify.py
#
# 왜 파일이냐: 클라우드/백그라운드로 돌 땐 볼 콘솔이 없다.
# 그래서 화면 출력 대신 '파일'로 남겨야 나중에 열어볼 수 있다. (repo에 커밋됨)

import json
import logging
import os
from collections import Counter
from datetime import datetime, timedelta, timezone

import logconf

log = logging.getLogger(__name__)

BRIEFING_PATH = "briefing.md"

# 왜 타임존을 박아두나:
#   datetime.now()는 '실행하는 컴퓨터의 로컬 시간'을 쓴다.
#   내 PC에서 돌리면 KST지만 GitHub Actions 러너는 UTC라서,
#   09:00 KST에 만든 브리핑에 00:00이 찍히는 사고가 난다.
#   실행 위치와 무관하게 항상 KST로 고정한다.
KST = timezone(timedelta(hours=9))

Item = dict[str, str]
# steam_metrics.Metric과 같은 모양이지만, 모듈 간 결합을 늘리지 않으려고
# import 대신 이 파일에서 다시 선언한다(Item도 같은 방식으로 다뤄왔다).
SteamMetric = dict[str, int | str]

# 왜 '키워드 자동 추출' 기능이 없나:
#   정규식 기반 단어 빈도 집계로 시도해봤지만, "게임"/"모바일" 같은 도메인
#   보일러플레이트가 항상 상위를 차지하거나 불용어를 필터링해도 인사이트가
#   나오지 않았다(JAW 판단, 2026-07-28). 진짜 트렌드 요약은 언어 이해가
#   필요한 작업이라 단순 카운팅으로는 안 된다는 결론.
#   대신 온디맨드로 처리한다: 트렌드가 궁금할 때 Claude Code 세션에서
#   briefing.md(들)를 직접 읽고 분석을 요청한다 — Day3/Day5/Day7에서
#   검증된 "Claude가 직접 읽고 쓰기" 방법론과 동일.


def source_counts(items: list[Item]) -> list[tuple[str, int]]:
    """이번 브리핑에서 소스별로 몇 건씩 나왔는지 집계한다."""
    counter: Counter[str] = Counter(item.get("source", "") for item in items)
    return [(source, count) for source, count in counter.most_common() if source]


def build_steam_section(metrics: list[SteamMetric]) -> list[str]:
    """Steam 동시 접속자 지표를 브리핑 줄 목록으로 조립한다.
    기사와 성격이 다른 지표라 헤더 아래 목록으로만 붙이고 번호는 매기지 않는다."""
    if not metrics:
        return []
    lines = ["## 📈 Steam 동시 접속자"]
    for m in metrics:
        game = m.get("game", "")
        players = m.get("players")
        if not game or players is None:
            continue
        lines.append(f"- {game} — {players:,}명")
    return lines


def build_briefing(items: list[Item], steam_metrics: list[SteamMetric] | None = None) -> str:
    """items(+선택적 steam_metrics) → 마크다운 브리핑 문자열로 조립해서 돌려준다."""
    now = datetime.now(KST).strftime("%Y-%m-%d %H:%M KST")
    lines = [f"# 🎮 게임 산업 브리핑 — {now}", f"> {len(items)}건 수집 · 검증 통과", ""]

    counts = source_counts(items)
    if counts:
        lines.append("## 📊 소스별 건수")
        lines.append(" · ".join(f"{source}: {count}건" for source, count in counts))
        lines.append("")

    lines.append("## 📰 기사 목록")
    for i, item in enumerate(items, start=1):
        title = item.get("title", "")
        url = item.get("url", "")
        date = item.get("date", "")
        source = item.get("source", "")
        lines.append(f"{i}. [{title}]({url}) — {date} · {source}")

    steam_lines = build_steam_section(steam_metrics or [])
    if steam_lines:
        lines.append("")
        lines += steam_lines

    return "\n".join(lines)


def notify(items: list[Item], steam_metrics: list[SteamMetric] | None = None) -> None:
    text = build_briefing(items, steam_metrics)
    with open(BRIEFING_PATH, "w", encoding="utf-8") as f:
        f.write(text)
    log.info(
        "브리핑 저장 → %s (%d건, Steam 지표 %d개)",
        BRIEFING_PATH, len(items), len(steam_metrics or []),
    )


def main() -> None:
    logconf.setup()
    with open("_workspace/final.json", encoding="utf-8") as f:
        items = json.load(f)

    steam_metrics: list[SteamMetric] = []
    steam_path = "_workspace/steam-metrics.json"
    if os.path.exists(steam_path):
        with open(steam_path, encoding="utf-8") as f:
            steam_metrics = json.load(f)

    notify(items, steam_metrics)


if __name__ == "__main__":
    main()
