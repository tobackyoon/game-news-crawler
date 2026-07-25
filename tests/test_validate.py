# validate 단위 테스트 (AAA 패턴).
# 데이터는 전부 합성값 — 실제 크롤링 결과를 쓰지 않는다.

import validate


def make_item(**overrides):
    """정상 아이템 하나. 필요한 필드만 바꿔 쓴다."""
    base = {
        "title": "제목1",
        "url": "https://example.com/1",
        "date": "July 2026",
        "source": "SensorTower",
    }
    return {**base, **overrides}


def make_items(count):
    """서로 다른 정상 아이템 count개."""
    return [
        make_item(title=f"제목{i}", url=f"https://example.com/{i}")
        for i in range(count)
    ]


def test_returns_pass_when_items_are_valid_and_sufficient():
    # Arrange
    items = make_items(validate.MIN_COUNT)

    # Act
    report = validate.validate(items)

    # Assert
    assert report["verdict"] == "PASS"
    assert report["problems"] == []


def test_returns_redo_when_item_count_is_below_minimum():
    # Arrange
    items = make_items(validate.MIN_COUNT - 1)

    # Act
    report = validate.validate(items)

    # Assert
    assert report["verdict"] == "REDO"
    assert any("수집 개수 부족" in p for p in report["problems"])


def test_returns_redo_when_title_is_empty():
    # Arrange
    items = make_items(validate.MIN_COUNT)
    items[0] = make_item(title="", url="https://example.com/0")

    # Act
    report = validate.validate(items)

    # Assert
    assert report["verdict"] == "REDO"
    assert any("title" in p for p in report["problems"])


def test_returns_redo_when_url_is_duplicated():
    # Arrange
    items = make_items(validate.MIN_COUNT)
    items[-1] = make_item(title="다른 제목", url=items[0]["url"])

    # Act
    report = validate.validate(items)

    # Assert
    assert report["verdict"] == "REDO"
    assert any("중복" in p for p in report["problems"])


def test_empty_urls_are_reported_as_missing_not_as_duplicates():
    """빈 url이 여러 개여도 '중복'으로 또 세지 않는다.
    이미 '빔/누락'으로 보고한 문제를 두 번 세면 진짜 중복이 묻힌다."""
    # Arrange
    items = make_items(validate.MIN_COUNT)
    items[0] = make_item(url="")
    items[1] = make_item(url="")

    # Act
    report = validate.validate(items)

    # Assert
    assert not any("중복" in p for p in report["problems"])
    assert sum("url 빔/누락" in p for p in report["problems"]) == 2


def test_returns_redo_for_empty_input():
    # Arrange / Act
    report = validate.validate([])

    # Assert
    assert report["verdict"] == "REDO"
