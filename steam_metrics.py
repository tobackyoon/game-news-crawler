# steam_metrics (지표 수집): Steam Web API에서 게임별 실시간 동시 접속자 수를 가져온다.
# 실행: repo 루트에서  python steam_metrics.py
#
# 대상: ISteamUserStats/GetNumberOfCurrentPlayers (공식, Valve)
#   무료 · API 키 불필요 · 공식 엔드포인트라 robots.txt 제약 없음
#   주의: 스팀은 다운로드 수/판매량 자체를 공개하지 않는다.
#   그래서 "다운로드"의 대안 지표로 실시간 동시 접속자 수를 쓴다.
#
# collect.py의 기사({title, url, date, source})와는 데이터 성격이 달라
# 별도 모듈로 분리했다. 기사 파이프라인(validate/state)과는 섞지 않고,
# notify.py가 브리핑에 별도 섹션으로만 붙인다.
#
# 출력: _workspace/steam-metrics.json ({appid, game, players, timestamp} 리스트)

import json
import logging
import os
from datetime import datetime, timedelta, timezone

import requests

import logconf

log = logging.getLogger(__name__)

API_BASE = "https://api.steampowered.com/ISteamUserStats/GetNumberOfCurrentPlayers/v1/"
OUT = "_workspace/steam-metrics.json"
TIMEOUT = 15

# notify.py와 동일한 이유로 타임존을 박아둔다 — GitHub Actions 러너는 UTC라서
# datetime.now()를 그냥 쓰면 실행 위치에 따라 시각이 흔들린다.
KST = timezone(timedelta(hours=9))

# 감시 대상 게임. appid는 스토어 URL(store.steampowered.com/app/<appid>)에서 확인한다.
# 게임 산업 브리핑과 맥락이 겹치는 라이브서비스·화제작 위주로 소수만 고정했다.
WATCHLIST: tuple[tuple[int, str], ...] = (
    (730, "Counter-Strike 2"),
    (570, "Dota 2"),
    (578080, "PUBG: BATTLEGROUNDS"),
    (1086940, "Baldur's Gate 3"),
    (1091500, "Cyberpunk 2077"),
)

Metric = dict[str, int | str]


def fetch_player_count(appid: int) -> int | None:
    """단일 appid의 실시간 동시 접속자 수를 가져온다.
    API가 result != 1로 답하면(존재하지 않는 appid 등) None을 돌려준다."""
    r = requests.get(API_BASE, params={"appid": appid}, timeout=TIMEOUT)
    r.raise_for_status()
    result = r.json().get("response", {})
    if result.get("result") != 1:
        log.warning("appid %d 응답 이상: %s", appid, result)
        return None
    return result.get("player_count")


def collect_players(watchlist: tuple[tuple[int, str], ...] = WATCHLIST) -> list[Metric]:
    """감시 목록의 각 게임에 대해 {appid, game, players, timestamp}를 수집한다.

    한 게임이 실패(타임아웃·차단 등)해도 나머지는 계속 수집한다
    (collect.py의 safe()와 동일한 격리 원칙)."""
    now = datetime.now(KST).isoformat(timespec="seconds")
    items: list[Metric] = []
    for appid, name in watchlist:
        try:
            count = fetch_player_count(appid)
        except Exception as e:
            log.warning("appid %d(%s) 실패 → 건너뜀: %s: %s", appid, name, type(e).__name__, e)
            continue
        if count is None:
            continue
        items.append({"appid": appid, "game": name, "players": count, "timestamp": now})
    return items


def main() -> None:
    logconf.setup()
    items = collect_players()

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)

    log.info("Steam 동접자 수집 완료: %d개 → %s", len(items), OUT)


if __name__ == "__main__":
    main()
