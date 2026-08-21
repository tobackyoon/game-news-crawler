# steam_metrics 단위 테스트 (AAA 패턴).
# Steam Web API(ISteamUserStats/GetNumberOfCurrentPlayers)는 공식 엔드포인트라
# robots.txt 문제가 없고 API 키도 필요 없다. 네트워크는 mocking해서 타지 않는다.

from datetime import datetime, timedelta

import steam_metrics


class FakeJsonResponse:
    """requests.Response 중 파서가 실제로 쓰는 것만 흉내낸다."""

    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def ok_payload(count):
    return {"response": {"result": 1, "player_count": count}}


def test_fetch_player_count_returns_count_on_success(monkeypatch):
    # Arrange
    monkeypatch.setattr(
        steam_metrics.requests, "get", lambda *a, **kw: FakeJsonResponse(ok_payload(412301))
    )

    # Act
    count = steam_metrics.fetch_player_count(578080)

    # Assert
    assert count == 412301


def test_fetch_player_count_returns_none_when_result_is_not_1(monkeypatch):
    """존재하지 않는 appid 등, API가 result != 1로 답하면 실패로 본다."""
    # Arrange
    monkeypatch.setattr(
        steam_metrics.requests, "get",
        lambda *a, **kw: FakeJsonResponse({"response": {"result": 42}}),
    )

    # Act
    count = steam_metrics.fetch_player_count(0)

    # Assert
    assert count is None


def test_collect_players_builds_metric_dicts(monkeypatch):
    # Arrange
    monkeypatch.setattr(
        steam_metrics.requests, "get", lambda *a, **kw: FakeJsonResponse(ok_payload(100))
    )
    watchlist = ((730, "Counter-Strike 2"),)

    # Act
    result = steam_metrics.collect_players(watchlist)

    # Assert
    assert len(result) == 1
    assert result[0]["appid"] == 730
    assert result[0]["game"] == "Counter-Strike 2"
    assert result[0]["players"] == 100
    assert result[0]["timestamp"]


def test_collect_players_stamps_timestamp_in_kst(monkeypatch):
    """notify.py와 동일한 이유로 KST 고정 — 러너가 UTC여도 시각이 안 흔들려야 한다."""
    # Arrange
    monkeypatch.setattr(
        steam_metrics.requests, "get", lambda *a, **kw: FakeJsonResponse(ok_payload(1))
    )
    watchlist = ((730, "Counter-Strike 2"),)

    # Act
    result = steam_metrics.collect_players(watchlist)

    # Assert
    stamped = datetime.fromisoformat(result[0]["timestamp"])
    assert stamped.utcoffset() == timedelta(hours=9)


def test_collect_players_skips_a_game_when_its_request_fails(monkeypatch):
    """한 게임이 실패해도 나머지는 수집된다 (collect.py의 safe()와 동일 원칙)."""
    # Arrange
    def flaky_get(*args, **kwargs):
        appid = kwargs.get("params", {}).get("appid")
        if appid == 730:
            raise RuntimeError("타임아웃")
        return FakeJsonResponse(ok_payload(50))

    monkeypatch.setattr(steam_metrics.requests, "get", flaky_get)
    watchlist = ((730, "Counter-Strike 2"), (570, "Dota 2"))

    # Act
    result = steam_metrics.collect_players(watchlist)

    # Assert
    assert [m["game"] for m in result] == ["Dota 2"]


def test_collect_players_skips_a_game_when_result_is_not_1(monkeypatch):
    # Arrange
    monkeypatch.setattr(
        steam_metrics.requests, "get",
        lambda *a, **kw: FakeJsonResponse({"response": {"result": 42}}),
    )
    watchlist = ((730, "Counter-Strike 2"),)

    # Act
    result = steam_metrics.collect_players(watchlist)

    # Assert
    assert result == []


def test_collect_players_uses_module_watchlist_by_default(monkeypatch):
    # Arrange
    monkeypatch.setattr(
        steam_metrics.requests, "get", lambda *a, **kw: FakeJsonResponse(ok_payload(1))
    )

    # Act
    result = steam_metrics.collect_players()

    # Assert
    assert len(result) == len(steam_metrics.WATCHLIST)
