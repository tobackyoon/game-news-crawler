# notify (알림 단계): 검증 통과 데이터를 '게임 산업 브리핑' 문서로 남긴다.
# 실행(단독 테스트): repo 루트에서  python notify.py
#
# 왜 파일이냐: 클라우드/백그라운드로 돌 땐 볼 콘솔이 없다.
# 그래서 화면 print 대신 '파일'로 남겨야 나중에 열어볼 수 있다. (repo에 커밋됨)

import json
import sys
from datetime import datetime

sys.stdout.reconfigure(encoding="utf-8")

BRIEFING_PATH = "briefing.md"


def build_briefing(items):
    """items → 마크다운 브리핑 문자열로 조립해서 돌려준다."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [f"# 🎮 게임 산업 브리핑 — {now}", f"> {len(items)}건 수집 · 검증 통과", ""]

    for i, item in enumerate(items, start=1):
        lines.append(f"{i}. [{item['title']}]({item['url']}) — {item['date']} · {item['source']}")

    return "\n".join(lines)


def notify(items):
    text = build_briefing(items)
    with open(BRIEFING_PATH, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"[알림] 브리핑 저장 → {BRIEFING_PATH} ({len(items)}건)")


def main():
    with open("_workspace/final.json", encoding="utf-8") as f:
        items = json.load(f)
    notify(items)


if __name__ == "__main__":
    main()
