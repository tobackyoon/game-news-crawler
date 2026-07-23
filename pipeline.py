# pipeline (오케스트레이터): collect → validate 루프 → 변경감지 → briefing
# 실행: repo 루트에서
#   python pipeline.py            # 정상 흐름
#   python pipeline.py --inject   # 첫 수집에 결함 주입 → REDO 관찰용
#
# author→reviewer PASS/REDO 패턴:
#   PASS → (변경 있으면) 브리핑 / REDO → 재수집 (최대 2회) / 초과 → 경고 후 종료

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # 같은 폴더 모듈 import용

import collect as collector
import validate as validator
import notify as notifier
import state as state

sys.stdout.reconfigure(encoding="utf-8")

MAX_RETRY = 2
SAVE_PATH = "_workspace/final.json"


def run(inject=False):
    for attempt in range(1, MAX_RETRY + 2):  # 최초 1회 + 재시도 MAX_RETRY회
        print(f"\n=== 시도 {attempt} ===")

        # ① 수집 — 첫 시도에만 결함 주입 (재수집은 정상 크롤링)
        items = collector.collect()
        if inject and attempt == 1:
            items = collector.inject_defects(items)
        print(f"수집: {len(items)}개")

        # ② 검증
        report = validator.validate(items)
        print(f"판정: {report['verdict']}")
        for p in report["problems"]:
            print(f"  - {p}")

        # ③ 분기
        if report["verdict"] == "PASS":
            # ③-1 변경 감지: 최신 글이 지난번과 같으면 브리핑 생략
            last = state.load_last_seen()
            if not state.has_changed(items, last):
                print("[변경 없음] 새 글이 없어 브리핑을 건너뜁니다.")
                return

            # ③-2 변경 있음 → 로컬 백업(json) + 브리핑(briefing.md) + 상태 갱신
            os.makedirs(os.path.dirname(SAVE_PATH), exist_ok=True)
            with open(SAVE_PATH, "w", encoding="utf-8") as f:
                json.dump(items, f, ensure_ascii=False, indent=2)
            notifier.notify(items)
            state.save_last_seen(items)
            print("[상태 갱신] 최신 글 시그니처 저장 완료 (_state/last_seen.json)")
            return

    # 루프 초과 — 무한루프 방지
    print("\n[경고] 재시도 한계 도달 — 수동 검토 권장. 파이프라인 중단.")


if __name__ == "__main__":
    run(inject="--inject" in sys.argv)
