# notify (알림 단계): 검증 통과 데이터를 '게임 산업 브리핑' 문서로 남긴다.
# 실행(단독 테스트): repo 루트에서  python notify.py
#
# 왜 파일이냐: 클라우드/백그라운드로 돌 땐 볼 콘솔이 없다.
# 그래서 화면 출력 대신 '파일'로 남겨야 나중에 열어볼 수 있다. (repo에 커밋됨)

import json
import logging
import re
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

# 영어 기사 제목에 흔한 불용어. 빈도 집계에서 의미 없는 상위권을 차지하는 걸 막는다.
_STOPWORDS = frozenset({
    "the", "a", "an", "and", "or", "to", "of", "in", "on", "for", "with",
    "is", "are", "how", "why", "what", "this", "that", "its", "it's", "new",
})

# 한글(가-힣)과 영단문자를 하나의 토큰으로 묶는다.
_WORD_RE = re.compile(r"[\w가-힣]+")


def _tokenize(title: str) -> list[str]:
    """제목에서 키워드 후보 토큰을 뽑는다.

    형태소 분석기를 쓰지 않는 단순 집계라, 한국어는 조사가 붙은 어절 그대로
    셈해진다(예: "게임이"와 "게임을"은 다른 단어로 집계됨). 더 정밀한 집계가
    필요해지면 konlpy 같은 형태소 분석기로 교체할 지점."""
    words = _WORD_RE.findall(title.lower())
    return [w for w in words if len(w) > 1 and w not in _STOPWORDS and not w.isdigit()]


def top_keywords(items: list[Item], top_n: int = 5) -> list[tuple[str, int]]:
    """모든 제목을 합쳐 가장 많이 등장한 키워드 top_n개를 (단어, 빈도)로 돌려준다."""
    counter: Counter[str] = Counter()
    for item in items:
        counter.update(_tokenize(item.get("title", "")))
    return counter.most_common(top_n)


def source_counts(items: list[Item]) -> list[tuple[str, int]]:
    """이번 브리핑에서 소스별로 몇 건씩 나왔는지 집계한다."""
    counter: Counter[str] = Counter(item.get("source", "") for item in items)
    return [(source, count) for source, count in counter.most_common() if source]


def build_briefing(items: list[Item]) -> str:
    """items → 마크다운 브리핑 문자열로 조립해서 돌려준다."""
    now = datetime.now(KST).strftime("%Y-%m-%d %H:%M KST")
    lines = [f"# 🎮 게임 산업 브리핑 — {now}", f"> {len(items)}건 수집 · 검증 통과", ""]

    counts = source_counts(items)
    if counts:
        lines.append("## 📊 소스별 건수")
        lines.append(" · ".join(f"{source}: {count}건" for source, count in counts))
        lines.append("")

    keywords = top_keywords(items)
    if keywords:
        lines.append("## 🔑 자주 언급된 키워드")
        lines.append(", ".join(f"{word}({count})" for word, count in keywords))
        lines.append("")

    lines.append("## 📰 기사 목록")
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
