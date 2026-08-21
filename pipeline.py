# pipeline (오케스트레이터): collect → validate 루프 → 변경감지 → briefing
# 실행: repo 루트에서
#   python pipeline.py            # 정상 흐름
#   python pipeline.py --inject   # 첫 수집에 결함 주입 → REDO 관찰용
#
# author→reviewer PASS/REDO 패턴:
#   PASS → (변경 있으면) 브리핑 / REDO → 재수집 (최대 2회) / 초과 → 실패로 종료

import json
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # 같은 폴더 모듈 import용

import collect as collector
import logconf
import notify as notifier
import state as state
import steam_metrics as steam
import validate as validator

log = logging.getLogger(__name__)

MAX_RETRY = 2
SAVE_PATH = "_workspace/final.json"


def run(inject: bool = False) -> bool:
    """파이프라인을 한 번 돌린다.

    반환값: 성공하면 True, 재시도 한계까지 실패하면 False.
    '새 글이 없어 건너뜀'도 True다 — 할 일이 없었을 뿐 실패가 아니다.
    """
    for attempt in range(1, MAX_RETRY + 2):  # 최초 1회 + 재시도 MAX_RETRY회
        log.info("=== 시도 %d ===", attempt)

        # ① 수집 — 첫 시도에만 결함 주입 (재수집은 정상 크롤링)
        items = collector.collect()
        if inject and attempt == 1:
            items = collector.inject_defects(items)
        log.info("수집: %d개", len(items))

        # ② 검증
        report = validator.validate(items)
        log.info("판정: %s", report["verdict"])
        for p in report["problems"]:
            log.info("  - %s", p)

        # ③ 분기
        if report["verdict"] == "PASS":
            # ③-1 변경 감지: 최신 글이 지난번과 같으면 브리핑 생략
            last = state.load_last_seen()
            if not state.has_changed(items, last):
                log.info("변경 없음 — 새 글이 없어 브리핑을 건너뜁니다.")
                return True

            # ③-2 변경 있음 → 로컬 백업(json) + 브리핑(briefing.md) + 상태 갱신
            os.makedirs(os.path.dirname(SAVE_PATH), exist_ok=True)
            with open(SAVE_PATH, "w", encoding="utf-8") as f:
                json.dump(items, f, ensure_ascii=False, indent=2)
            # Steam 지표는 기사 변경 감지(state)와 무관한 실시간 스냅샷이라,
            # 브리핑을 새로 쓸 때만 같이 갱신한다 (건너뛸 땐 API 호출도 안 함).
            notifier.notify(items, steam.collect_players())
            state.save_last_seen(items)
            log.info("상태 갱신 — 최신 글 시그니처 저장 완료 (%s)", state.STATE_PATH)
            return True

    # 루프 초과 — 무한루프 방지
    log.error("재시도 한계 도달 — 수동 검토 필요. 파이프라인 중단.")
    return False


if __name__ == "__main__":
    logconf.setup()
    # 왜 종료 코드를 넘기나:
    #   실패했는데 0으로 끝나면 GitHub Actions가 초록불로 표시된다.
    #   크롤링이 몇 주째 죽어 있어도 아무도 모르는 상태가 된다.
    #   실패는 실패로 보여야 알아챈다.
    sys.exit(0 if run(inject="--inject" in sys.argv) else 1)
