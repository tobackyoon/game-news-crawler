# notify 단위 테스트 (AAA 패턴).
# 브리핑 파일은 tmp_path로 격리한다 — 실제 briefing.md를 덮어쓰지 않는다.

from datetime import datetime, timedelta

import notify


def make_items(count):
    return [
        {
            "title": f"제목{i}",
            "url": f"https://example.com/{i}",
            "date": "July 2026",
            "source": "테스트",
        }
        for i in range(count)
    ]


class FixedDatetime:
    """datetime.now(tz)에 어떤 타임존이 넘어왔는지 붙잡아두는 스텁."""

    captured_tz = None

    @classmethod
    def now(cls, tz=None):
        cls.captured_tz = tz
        return datetime(2026, 7, 23, 9, 0, tzinfo=tz)


def test_kst_constant_is_utc_plus_9():
    # Act / Assert
    assert notify.KST.utcoffset(None) == timedelta(hours=9)


def test_briefing_header_uses_kst_not_the_runner_local_time(monkeypatch):
    """datetime.now()를 그냥 쓰면 Actions 러너(UTC)에서 00시가 찍힌다.
    실행 위치와 무관하게 KST가 넘어가는지 확인한다."""
    # Arrange
    monkeypatch.setattr(notify, "datetime", FixedDatetime)

    # Act
    text = notify.build_briefing(make_items(1))

    # Assert
    assert FixedDatetime.captured_tz == notify.KST
    assert "2026-07-23 09:00 KST" in text


def test_briefing_lists_every_item_as_a_numbered_link():
    # Arrange
    items = make_items(3)

    # Act
    text = notify.build_briefing(items)

    # Assert
    assert "1. [제목0](https://example.com/0) — July 2026 · 테스트" in text
    assert "3. [제목2](https://example.com/2) — July 2026 · 테스트" in text
    assert "> 3건 수집 · 검증 통과" in text


def test_briefing_tolerates_items_missing_optional_fields():
    """date/source는 validate가 검사하지 않는 필드라 비어 있을 수 있다.
    여기서 KeyError로 죽으면 브리핑 전체가 날아간다."""
    # Arrange
    items = [{"title": "제목", "url": "https://example.com/1"}]

    # Act
    text = notify.build_briefing(items)

    # Assert
    assert "1. [제목](https://example.com/1)" in text


def test_notify_writes_the_briefing_file(tmp_path, monkeypatch):
    # Arrange
    path = tmp_path / "briefing.md"
    monkeypatch.setattr(notify, "BRIEFING_PATH", str(path))

    # Act
    notify.notify(make_items(2))

    # Assert
    assert "> 2건 수집 · 검증 통과" in path.read_text(encoding="utf-8")
