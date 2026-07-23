# collect (author 역할): 크롤링 + 구조화 추출
# 실행: repo 루트에서
#   python collect.py            # 정상 수집
#   python collect.py --inject   # 일부러 결함 주입 (검증 루프 테스트용)
#
# 대상 (robots 허용 + 서버렌더링 확인됨):
#   - SensorTower 블로그: https://sensortower.com/ko/blog
#   - (참고) Newzoo는 Cloudflare 봇 차단으로 자동 크롤링 불가 → 함수만 보존, SOURCES에서 제외
# 출력: _workspace/crawl-result.json  ({title, url, date, source} 리스트)

import requests
from bs4 import BeautifulSoup
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
OUT = "_workspace/crawl-result.json"
PER_SOURCE = 10  # 소스별 최신 몇 개까지만 담을지 (브리핑이 너무 길어지지 않게)


def collect_sensortower():
    """SensorTower 블로그 카드에서 {title, url, date} 추출."""
    r = requests.get("https://sensortower.com/ko/blog", headers=HEADERS, timeout=15)
    r.raise_for_status()
    r.encoding = "utf-8"
    soup = BeautifulSoup(r.text, "html.parser")

    items = []
    for card in soup.select("div.MuiCard-root.has-link"):
        h3 = card.select_one("h3")                       # 제목
        h4 = card.select_one("h4")                       # "카테고리 • 날짜"
        a = card.select_one('a[href^="/ko/blog/"]')       # 링크
        title = h3.get_text(strip=True) if h3 else ""
        date = h4.get_text(strip=True) if h4 else ""
        url = "https://sensortower.com" + a["href"] if (a and a.has_attr("href")) else ""
        if not title:
            continue
        items.append({"title": title, "url": url, "date": date, "source": "SensorTower"})
    return items[:PER_SOURCE]


def collect_newzoo():
    """Newzoo 아티클 카드에서 {title, url, date} 추출.
    주의: Newzoo는 Cloudflare 봇 차단이 있어 자동 실행에선 403이 잦다.
    지금은 SOURCES에서 제외돼 있고, 참고/재활용을 위해 함수만 남겨둔다."""
    r = requests.get("https://newzoo.com/articles", headers=HEADERS, timeout=15)
    r.raise_for_status()
    r.encoding = "utf-8"
    soup = BeautifulSoup(r.text, "html.parser")

    items = []
    for card in soup.select("div.article-cell"):
        h3 = card.select_one("h3.case-card-title")        # 제목
        t = card.select_one("time.article-meta-date")     # 날짜 "July 16, 2026"
        a = card.select_one('a[href^="/articles/"]')       # 링크
        title = h3.get_text(strip=True) if h3 else ""
        date = t.get_text(strip=True) if t else ""
        url = "https://newzoo.com" + a["href"] if (a and a.has_attr("href")) else ""
        if not title:
            continue
        items.append({"title": title, "url": url, "date": date, "source": "Newzoo"})
    return items[:PER_SOURCE]


def safe(fn):
    """한 소스가 실패(차단·타임아웃 등)해도 전체가 죽지 않게 감싼다.
    실패하면 경고만 남기고 빈 리스트를 돌려준다 (복원력)."""
    try:
        return fn()
    except Exception as e:
        print(f"[경고] {fn.__name__} 실패 → 건너뜀: {type(e).__name__}: {e}")
        return []


# 현재 활성 소스 목록. 소스를 추가하려면 이 튜플에 함수를 넣으면 된다.
SOURCES = (collect_sensortower,)


def collect():
    """등록된 소스들을 합쳐 하나의 리스트로. 한 소스가 막혀도 나머지는 수집된다."""
    items = []
    for source_fn in SOURCES:
        items += safe(source_fn)
    return items


def inject_defects(items):
    """검증 루프를 실제로 테스트하려면 '실패하는 데이터'가 필요하다.
    happy path만 있으면 REDO가 절대 안 뜨므로, --inject로 결함을 심는다."""
    if not items:
        return items
    items = list(items)
    items[0] = {**items[0], "title": ""}   # 필수 필드 빔
    items.append(dict(items[1]))            # 중복 항목
    return items


def main():
    inject = "--inject" in sys.argv
    items = collect()
    if inject:
        items = inject_defects(items)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)

    print(f"수집 완료: {len(items)}개 → {OUT}" + (" (결함 주입됨)" if inject else ""))


if __name__ == "__main__":
    main()
