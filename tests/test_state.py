# state 단위 테스트 (AAA 패턴).
# 상태 파일은 tmp_path로 격리한다 — 실제 _state/last_seen.json을 건드리지 않는다.

import state


def make_item(source, url):
    return {"title": f"{source} 최신글", "url": url, "date": "July 2026", "source": source}


def test_newest_signature_takes_the_first_item_of_each_source():
    # Arrange
    items = [
        make_item("A", "https://example.com/a-new"),
        make_item("A", "https://example.com/a-old"),
        make_item("B", "https://example.com/b-new"),
    ]

    # Act
    sig = state.newest_signature(items)

    # Assert
    assert sig == {"A": "https://example.com/a-new", "B": "https://example.com/b-new"}


def test_has_changed_is_true_on_first_run():
    # Arrange
    items = [make_item("A", "https://example.com/a")]

    # Act / Assert
    assert state.has_changed(items, {}) is True


def test_has_changed_is_false_when_newest_is_identical():
    # Arrange
    items = [make_item("A", "https://example.com/a")]

    # Act / Assert
    assert state.has_changed(items, {"A": "https://example.com/a"}) is False


def test_has_changed_ignores_a_source_missing_from_this_run():
    """B 수집이 실패해 이번 결과에서 빠져도 '변경'으로 보지 않는다.
    사라진 것과 바뀐 것은 다르다 — 실패를 새 글로 오인하면 안 된다."""
    # Arrange
    items = [make_item("A", "https://example.com/a")]
    last = {"A": "https://example.com/a", "B": "https://example.com/b"}

    # Act / Assert
    assert state.has_changed(items, last) is False


def test_save_last_seen_keeps_sources_missing_from_this_run(tmp_path, monkeypatch):
    """실패한 소스의 기록을 덮어써서 지우면, 다음 실행에 그 소스가
    복구됐을 때 안 바뀐 글을 '새 글'로 오인한다."""
    # Arrange
    monkeypatch.setattr(state, "STATE_PATH", str(tmp_path / "last_seen.json"))
    state.save_last_seen(
        [make_item("A", "https://example.com/a1"), make_item("B", "https://example.com/b1")]
    )

    # Act — 이번 실행에선 B가 실패해 빠졌다
    state.save_last_seen([make_item("A", "https://example.com/a2")])

    # Assert
    assert state.load_last_seen() == {
        "A": "https://example.com/a2",
        "B": "https://example.com/b1",
    }


def test_load_last_seen_returns_empty_dict_when_file_is_missing(tmp_path, monkeypatch):
    # Arrange
    monkeypatch.setattr(state, "STATE_PATH", str(tmp_path / "없는파일.json"))

    # Act / Assert
    assert state.load_last_seen() == {}
