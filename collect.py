# collect (author 역할): 크롤링 + 구조화 추출
# 실행: repo 루트에서
#   python collect.py            # 정상 수집
#   python collect.py --inject   # 일부러 결함 주입 (검증 루프 테스트용)
#
# 대상 (robots 허용 + 서버렌더링 확인됨):
#   - SensorTower 블로그: https://sensortower.com/ko/blog
#   - naavik 사이트: https://naavik.co
#   - PocketGamer.biz 뉴스: https://www.pocketgamer.biz/news/
#   - (참고) Newzoo는 Cloudflare 봇 차단으로 자동 크롤링 불가 → 함수만 보존, SOURCES에서 제외
#   - (참고) GameDeveloper.com은 robots.txt가 ClaudeBot을 명시적으로 차단 → 후보에서 기각
#   - (참고) TouchArcade는 요청 자체가 403 → 후보에서 기각
# 출력: _workspace/crawl-result.json  ({title, url, date, source} 리스트)

import json
import logging
import os
import sys
from collections.abc import Callable
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

import logconf

log = logging.getLogger(__name__)

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
OUT = "_workspace/crawl-result.json"
PER_SOURCE = 10  # 소스별 최신 몇 개까지만 담을지 (브리핑이 너무 길어지지 않게)
TIMEOUT = 15     # 초. 응답 없는 사이트에 매달려 있지 않게.

SENSORTOWER_BASE = "https://sensortower.com"
NAAVIK_BASE = "https://naavik.co"
NEWZOO_BASE = "https://newzoo.com"
POCKETGAMER_BASE = "https://www.pocketgamer.biz"

Item = dict[str, str]
Source = Callable[[], list[Item]]


def collect_sensortower() -> list[Item]:
    """SensorTower 블로그 카드에서 {title, url, date} 추출."""
    r = requests.get(f"{SENSORTOWER_BASE}/ko/blog", headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    r.encoding = "utf-8"
    soup = BeautifulSoup(r.text, "html.parser")

    items: list[Item] = []
    for card in soup.select("div.MuiCard-root.has-link"):
        h3 = card.select_one("h3")                       # 제목
        h4 = card.select_one("h4")                       # "카테고리 • 날짜"
        a = card.select_one('a[href^="/ko/blog/"]')       # 링크
        title = h3.get_text(strip=True) if h3 else ""
        date = h4.get_text(strip=True) if h4 else ""
        # urljoin: href가 절대 URL로 바뀌어도 안 깨진다. 문자열 접합이면 주소가 두 번 붙는다.
        url = urljoin(SENSORTOWER_BASE, a["href"]) if (a and a.has_attr("href")) else ""
        if not title:
            continue
        items.append({"title": title, "url": url, "date": date, "source": "SensorTower"})
    return items[:PER_SOURCE]


def _is_digest_link(href: str | None) -> bool:
    """목록/카테고리 페이지 자체가 아니라 개별 digest 글 링크인지."""
    if not href or "/digest/" not in href:
        return False
    excluded = (f"{NAAVIK_BASE}/digest", f"{NAAVIK_BASE}/category/digest")
    return href.rstrip("/") not in excluded


def collect_naavik() -> list[Item]:
    """Naavik digest 목록에서 {title, url, date} 추출.
    주의: 카드 wrapper가 없어 title/time을 각각 따로 뽑아 순번으로 짝짓는다.
    페이지 구조가 바뀌어 개수가 어긋나면 경고만 남기고 넘어간다(조용한 실패 방지)."""
    r = requests.get(f"{NAAVIK_BASE}/digest/", headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    r.encoding = "utf-8"
    soup = BeautifulSoup(r.text, "html.parser")

    titles = soup.select("h1.entry-title, h3.wp-block-post-title")
    times = soup.select("time[datetime]")
    if len(titles) != len(times):
        log.warning(
            "Naavik 제목(%d개)과 time(%d개) 개수가 다름 → 순번 매칭이 밀렸을 수 있음",
            len(titles), len(times),
        )

    items: list[Item] = []
    for i, title_el in enumerate(titles):
        title = title_el.get_text(strip=True)
        a = title_el.find("a") or title_el.find_next("a", href=_is_digest_link)
        date = times[i].get_text(strip=True) if i < len(times) else ""
        url = urljoin(NAAVIK_BASE, a["href"]) if (a and a.has_attr("href")) else ""
        if not title:
            continue
        items.append({"title": title, "url": url, "date": date, "source": "Naavik"})
    return items[:PER_SOURCE]


def collect_pocketgamer() -> list[Item]:
    """PocketGamer.biz 뉴스 목록에서 {title, url, date} 추출.
    상단 '피처드/팟캐스트' 카드(class="feat")는 날짜 태그가 없어 대상에서 빠지고,
    본문 목록(div.result-set.articles 안의 article)만 사용한다."""
    r = requests.get(f"{POCKETGAMER_BASE}/news/", headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    r.encoding = "utf-8"
    soup = BeautifulSoup(r.text, "html.parser")

    items: list[Item] = []
    result_set = soup.select_one("div.result-set.articles")
    cards = result_set.select("article") if result_set else []
    for card in cards:
        a = card.select_one("a[href]")
        h1 = card.select_one("h1")
        time_el = card.select_one("time[datetime]")
        title = h1.get_text(strip=True) if h1 else ""
        date = time_el.get_text(strip=True) if time_el else ""
        url = urljoin(POCKETGAMER_BASE, a["href"]) if (a and a.has_attr("href")) else ""
        if not title:
            continue
        items.append({"title": title, "url": url, "date": date, "source": "PocketGamer.biz"})
    return items[:PER_SOURCE]


def collect_newzoo() -> list[Item]:
    """Newzoo 아티클 카드에서 {title, url, date} 추출.
    주의: Newzoo는 Cloudflare 봇 차단이 있어 자동 실행에선 403이 잦다.
    지금은 SOURCES에서 제외돼 있고, 참고/재활용을 위해 함수만 남겨둔다."""
    r = requests.get(f"{NEWZOO_BASE}/articles", headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    r.encoding = "utf-8"
    soup = BeautifulSoup(r.text, "html.parser")

    items: list[Item] = []
    for card in soup.select("div.article-cell"):
        h3 = card.select_one("h3.case-card-title")        # 제목
        t = card.select_one("time.article-meta-date")     # 날짜 "July 16, 2026"
        a = card.select_one('a[href^="/articles/"]')       # 링크
        title = h3.get_text(strip=True) if h3 else ""
        date = t.get_text(strip=True) if t else ""
        url = urljoin(NEWZOO_BASE, a["href"]) if (a and a.has_attr("href")) else ""
        if not title:
            continue
        items.append({"title": title, "url": url, "date": date, "source": "Newzoo"})
    return items[:PER_SOURCE]


def safe(fn: Source) -> list[Item]:
    """한 소스가 실패(차단·타임아웃 등)해도 전체가 죽지 않게 감싼다.
    실패하면 경고만 남기고 빈 리스트를 돌려준다 (복원력).

    주의: 여기서 삼킨 예외가 '조용한 실패'로 끝나면 안 된다.
    소스가 전멸하면 validate가 REDO를 내고, 최종적으로 pipeline이
    0이 아닌 종료 코드로 끝내 CI를 빨간불로 만든다."""
    try:
        return fn()
    except Exception as e:
        log.warning("%s 실패 → 건너뜀: %s: %s", fn.__name__, type(e).__name__, e)
        return []


# 현재 활성 소스 목록. 소스를 추가하려면 이 튜플에 함수를 넣으면 된다.
SOURCES: tuple[Source, ...] = (collect_sensortower, collect_naavik, collect_pocketgamer)


def collect() -> list[Item]:
    """등록된 소스들을 합쳐 하나의 리스트로. 한 소스가 막혀도 나머지는 수집된다."""
    items: list[Item] = []
    for source_fn in SOURCES:
        items += safe(source_fn)
    return items


def inject_defects(items: list[Item]) -> list[Item]:
    """검증 루프를 실제로 테스트하려면 '실패하는 데이터'가 필요하다.
    happy path만 있으면 REDO가 절대 안 뜨므로, --inject로 결함을 심는다."""
    if not items:
        return items
    items = list(items)
    items[0] = {**items[0], "title": ""}   # 필수 필드 빔
    items.append(dict(items[1]))            # 중복 항목
    return items


def main() -> None:
    logconf.setup()
    inject = "--inject" in sys.argv
    items = collect()
    if inject:
        items = inject_defects(items)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)

    log.info("수집 완료: %d개 → %s%s", len(items), OUT, " (결함 주입됨)" if inject else "")


if __name__ == "__main__":
    main()
