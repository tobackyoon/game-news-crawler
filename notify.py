# notify (알림 단계): 검증 통과 데이터를 '게임 산업 브리핑' 문서로 남긴다.
# 실행(단독 테스트): repo 루트에서  python notify.py
#
# 왜 파일이냐: 클라우드/백그라운드로 돌 땐 볼 콘솔이 없다.
# 그래서 화면 출력 대신 '파일'로 남겨야 나중에 열어볼 수 있다. (repo에 커밋됨)

import json
import logging
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


def build_briefing(items: list[Item]) -> str:
    """items → 마크다운 브리핑 문자열로 조립해서 돌려준다."""
    now = datetime.now(KST).strftime("%Y-%m-%d %H:%M KST")
    lines = [f"# 🎮 게임 산업 브리핑 — {now}", f"> {len(items)}건 수집 · 검증 통과", ""]

    for i, item in enumerate(items, start=1):
        title = item.get("title", "")
        url = item.get("url", "")
        date = item.get("date", "")
        source = item.get("source", "")
        lines.append(f"{i}. [{title}]({url}) — {date} · {source}")

    return "\n".join(lines)


def notify(items: list[Item]) -> None:
    text = build_briefing(items)
    with open(BRIEFING_PATH, "w", encoding="utf-8") as f:
        f.write(text)
    log.info("브리핑 저장 → %s (%d건)", BRIEFING_PATH, len(items))


def main() -> None:
    logconf.setup()
    with open("_workspace/final.json", encoding="utf-8") as f:
        items = json.load(f)
    notify(items)


if __name__ == "__main__":
    main()
