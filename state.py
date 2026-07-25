# state (변경 감지): "지난번에 본 최신 글"을 기억하고 비교한다.
#
# 왜: 클라우드(GitHub Actions)는 실행이 끝나면 파일이 사라진다(휘발성).
#     그래서 "각 소스의 최신 글 URL"을 state 파일에 남겨 repo에 커밋한다.
#     다음 실행 때 이 파일을 읽어 최신 글이 그대로면 → 저장/브리핑을 건너뛴다.
#
# state 파일 형식(예):
#   { "SensorTower": "https://.../ko/blog/xxx" }

import json
import os

STATE_PATH = "_state/last_seen.json"

Item = dict[str, str]
Signature = dict[str, str]


def newest_signature(items: list[Item]) -> Signature:
    """각 소스의 '맨 앞(최신) 글 URL'을 뽑아 시그니처로 만든다.
    collect()가 소스별로 최신순으로 담아주므로, 소스별 첫 등장이 최신이다."""
    sig: Signature = {}
    for item in items:
        src = item.get("source", "")
        if src and src not in sig:
            sig[src] = item.get("url", "")
    return sig


def load_last_seen() -> Signature:
    """저장돼 있던 지난번 시그니처를 읽는다. 없으면 빈 dict."""
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {}


def has_changed(items: list[Item], last: Signature) -> bool:
    """이번에 수집된 소스 중 하나라도 최신 글이 지난번과 다르면 True.

    주의: dict 전체를 통째로 비교하면 안 된다.
    수집에 실패해 이번 결과에서 빠진 소스가 있으면 dict가 달라지므로
    '새 글이 있다'로 오인한다. 사라진 것과 바뀐 것은 다르다.
    그래서 '이번에 실제로 수집된 소스'만 비교 대상으로 삼는다."""
    return any(last.get(src) != url for src, url in newest_signature(items).items())


def save_last_seen(items: list[Item]) -> None:
    """이번 시그니처를 기존 상태에 '병합'해서 저장한다.

    주의: 덮어쓰기가 아니라 병합이다.
    이번에 실패한 소스의 기록까지 지워버리면, 다음 실행에서 그 소스가
    복구됐을 때 실제로는 안 바뀐 글을 '새 글'로 오인해 브리핑이 또 나간다."""
    merged = {**load_last_seen(), **newest_signature(items)}
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)
