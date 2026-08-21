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


def test_source_counts_tallies_items_per_source_and_skips_blank_source():
    # Arrange
    items = [
        {"source": "SensorTower"},
        {"source": "SensorTower"},
        {"source": "Naavik"},
        {},
    ]

    # Act
    result = notify.source_counts(items)

    # Assert
    assert result[0] == ("SensorTower", 2)
    assert ("Naavik", 1) in result
    assert all(source for source, _ in result)


def test_briefing_includes_source_count_summary_section():
    # Arrange
    items = [
        {
            "title": "Genshin Impact revenue soars",
            "url": "https://example.com/1",
            "date": "July 2026",
            "source": "Naavik",
        },
        {
            "title": "Genshin Impact tops charts",
            "url": "https://example.com/2",
            "date": "July 2026",
            "source": "Naavik",
        },
    ]

    # Act
    text = notify.build_briefing(items)

    # Assert
    assert "## 📊 소스별 건수" in text
    assert "Naavik: 2건" in text


def test_notify_writes_the_briefing_file(tmp_path, monkeypatch):
    # Arrange
    path = tmp_path / "briefing.md"
    monkeypatch.setattr(notify, "BRIEFING_PATH", str(path))

    # Act
    notify.notify(make_items(2))

    # Assert
    assert "> 2건 수집 · 검증 통과" in path.read_text(encoding="utf-8")


# --- Steam 동시 접속자 섹션 ---------------------------------------------------
# 기사({title,url,date,source})와 성격이 다른 지표 데이터라 별도 섹션으로 붙인다.


def make_steam_metrics(count):
    return [
        {"appid": 100 + i, "game": f"게임{i}", "players": 1000 * (i + 1), "timestamp": "t"}
        for i in range(count)
    ]


def test_build_steam_section_returns_empty_when_no_metrics():
    # Act / Assert
    assert notify.build_steam_section([]) == []


def test_build_steam_section_skips_entries_missing_game_or_players():
    """한 게임의 API 응답이 이상해도(값 누락) 나머지 지표까지 브리핑이 깨지면 안 된다."""
    # Arrange
    metrics = [
        {"appid": 1, "game": "", "players": 10, "timestamp": "t"},
        {"appid": 2, "game": "게임2", "players": None, "timestamp": "t"},
        {"appid": 3, "game": "게임3", "players": 5, "timestamp": "t"},
    ]

    # Act
    lines = notify.build_steam_section(metrics)

    # Assert
    assert lines == ["## 📈 Steam 동시 접속자", "- 게임3 — 5명"]


def test_build_steam_section_lists_each_game_with_comma_formatted_players():
    # Arrange
    metrics = [{"appid": 730, "game": "Counter-Strike 2", "players": 412301, "timestamp": "t"}]

    # Act
    lines = notify.build_steam_section(metrics)

    # Assert
    assert "## 📈 Steam 동시 접속자" in lines
    assert "- Counter-Strike 2 — 412,301명" in lines


def test_build_briefing_appends_steam_section_when_metrics_given():
    # Arrange
    items = make_items(1)
    metrics = make_steam_metrics(1)

    # Act
    text = notify.build_briefing(items, steam_metrics=metrics)

    # Assert
    assert "## 📈 Steam 동시 접속자" in text
    assert "- 게임0 — 1,000명" in text


def test_build_briefing_omits_steam_section_when_no_metrics_given():
    # Act
    text = notify.build_briefing(make_items(1))

    # Assert
    assert "Steam" not in text


def test_notify_passes_steam_metrics_through_to_the_briefing(tmp_path, monkeypatch):
    # Arrange
    path = tmp_path / "briefing.md"
    monkeypatch.setattr(notify, "BRIEFING_PATH", str(path))

    # Act
    notify.notify(make_items(1), make_steam_metrics(1))

    # Assert
    assert "게임0 — 1,000명" in path.read_text(encoding="utf-8")
