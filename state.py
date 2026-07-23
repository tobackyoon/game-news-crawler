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


def newest_signature(items):
    """각 소스의 '맨 앞(최신) 글 URL'을 뽑아 시그니처로 만든다.
    collect()가 소스별로 최신순으로 담아주므로, 소스별 첫 등장이 최신이다."""
    sig = {}
    for item in items:
        src = item.get("source", "")
        if src and src not in sig:
            sig[src] = item.get("url", "")
    return sig


def load_last_seen():
    """저장돼 있던 지난번 시그니처를 읽는다. 없으면 빈 dict."""
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {}


def has_changed(items, last):
    """이번 최신 글이 지난번과 다르면 True (= 업데이트 있음)."""
    return newest_signature(items) != last


def save_last_seen(items):
    """이번 최신 글 시그니처를 state 파일에 저장한다."""
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(newest_signature(items), f, ensure_ascii=False, indent=2)
