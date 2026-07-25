# pipeline 통합 테스트 (AAA 패턴).
# 네트워크는 타지 않는다 — collector.collect를 합성 데이터로 갈아끼운다.
# 파일 출력은 전부 tmp_path로 격리한다.

import json

import pipeline


def make_items(count, source="테스트"):
    return [
        {
            "title": f"제목{i}",
            "url": f"https://example.com/{i}",
            "date": "July 2026",
            "source": source,
        }
        for i in range(count)
    ]


def redirect_outputs(monkeypatch, tmp_path):
    """브리핑·상태·백업 경로를 임시 폴더로 돌린다."""
    monkeypatch.setattr(pipeline, "SAVE_PATH", str(tmp_path / "final.json"))
    monkeypatch.setattr(pipeline.state, "STATE_PATH", str(tmp_path / "last_seen.json"))
    monkeypatch.setattr(pipeline.notifier, "BRIEFING_PATH", str(tmp_path / "briefing.md"))


def test_run_returns_false_when_retries_are_exhausted(monkeypatch):
    """수집이 계속 실패하면 실패로 끝나야 한다.
    여기서 True가 나오면 __main__이 종료 코드 0을 내보내고,
    GitHub Actions가 죽은 파이프라인을 초록불로 표시한다."""
    # Arrange — 모든 소스가 막혀 아무것도 못 걷은 상황
    monkeypatch.setattr(pipeline.collector, "collect", lambda: [])

    # Act
    result = pipeline.run()

    # Assert
    assert result is False


def test_run_retries_up_to_the_limit_before_giving_up(monkeypatch):
    # Arrange
    calls = []
    monkeypatch.setattr(pipeline.collector, "collect", lambda: calls.append(1) or [])

    # Act
    pipeline.run()

    # Assert
    assert len(calls) == pipeline.MAX_RETRY + 1


def test_run_writes_briefing_and_state_when_new_items_are_found(monkeypatch, tmp_path):
    # Arrange
    redirect_outputs(monkeypatch, tmp_path)
    monkeypatch.setattr(pipeline.collector, "collect", lambda: make_items(5))

    # Act
    result = pipeline.run()

    # Assert
    assert result is True
    assert (tmp_path / "briefing.md").exists()
    saved = json.loads((tmp_path / "last_seen.json").read_text(encoding="utf-8"))
    assert saved == {"테스트": "https://example.com/0"}


def test_run_skips_briefing_when_nothing_changed(monkeypatch, tmp_path):
    """새 글이 없으면 브리핑을 새로 쓰지 않는다 (낭비 방지).
    이것도 성공이다 — 할 일이 없었을 뿐이다."""
    # Arrange
    redirect_outputs(monkeypatch, tmp_path)
    monkeypatch.setattr(pipeline.collector, "collect", lambda: make_items(5))
    pipeline.run()  # 1회차: 브리핑 생성 + 상태 저장
    (tmp_path / "briefing.md").unlink()

    # Act — 2회차: 같은 데이터
    result = pipeline.run()

    # Assert
    assert result is True
    assert not (tmp_path / "briefing.md").exists()


def test_run_recovers_on_the_second_attempt_when_defects_were_injected(monkeypatch, tmp_path):
    """--inject는 1회차에만 결함을 심으므로 2회차엔 PASS로 회복돼야 한다."""
    # Arrange
    redirect_outputs(monkeypatch, tmp_path)
    monkeypatch.setattr(pipeline.collector, "collect", lambda: make_items(5))

    # Act
    result = pipeline.run(inject=True)

    # Assert
    assert result is True
    assert (tmp_path / "briefing.md").exists()
