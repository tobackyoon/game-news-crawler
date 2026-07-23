# validate (reviewer 역할): 수집 데이터 품질 검증
# 실행: repo 루트에서  python validate.py
#
# 입력: _workspace/crawl-result.json
# 출력: _workspace/review-report.json  ({verdict: PASS|REDO, problems: [...]})
#
# 규칙: 주관이 아닌 '객관적 기준'만 사용. 판정 불확실 시 PASS보다 REDO.

import json
import sys

sys.stdout.reconfigure(encoding="utf-8")

IN = "_workspace/crawl-result.json"
OUT = "_workspace/review-report.json"

MIN_COUNT = 5  # 최소 이만큼은 수집돼야 정상으로 본다


def check_count(items):
    problems = []
    if len(items) < MIN_COUNT:
        problems.append(f"수집 개수 부족: {len(items)}개 (최소 {MIN_COUNT}개)")
    return problems


def check_required_fields(items):
    """각 item에서 title 또는 url이 빈 문자열이거나 없는 경우를 잡는다."""
    problems = []
    for i, item in enumerate(items):
        if not item.get("title"):
            problems.append(f"{i}번 항목 title 빔/누락")
        if not item.get("url"):
            problems.append(f"{i}번 항목 url 빔/누락")
    return problems


def check_duplicates(items):
    """같은 url이 두 번 이상 나오면 중복."""
    problems = []
    seen = set()
    for i, item in enumerate(items):
        url = item.get("url")
        if url in seen:
            problems.append(f"{i}번 항목 url 중복: {url}")
        else:
            seen.add(url)
    return problems


def validate(items):
    problems = []
    problems += check_count(items)
    problems += check_required_fields(items)
    problems += check_duplicates(items)

    verdict = "PASS" if not problems else "REDO"
    return {"verdict": verdict, "problems": problems}


def main():
    with open(IN, encoding="utf-8") as f:
        items = json.load(f)

    report = validate(items)

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"판정: {report['verdict']}")
    for p in report["problems"]:
        print(f"  - {p}")


if __name__ == "__main__":
    main()
