# collect 단위 테스트 (AAA 패턴).
# 네트워크를 타는 collect_sensortower/collect_newzoo는 여기서 테스트하지 않는다.
# 순수 로직(safe, inject_defects)만 검증한다.

import collect


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


def test_safe_returns_empty_list_when_source_raises():
    """한 소스가 죽어도 나머지를 살리는 격리 장치."""
    # Arrange
    def blocked_source():
        raise RuntimeError("403 차단")

    # Act / Assert
    assert collect.safe(blocked_source) == []


def test_safe_passes_through_a_working_source():
    # Arrange
    expected = make_items(1)

    def working_source():
        return make_items(1)

    # Act / Assert
    assert collect.safe(working_source) == expected


def test_inject_defects_creates_an_empty_title_and_a_duplicate():
    # Arrange
    items = make_items(3)

    # Act
    result = collect.inject_defects(items)

    # Assert
    assert result[0]["title"] == ""
    assert len(result) == len(items) + 1


def test_inject_defects_does_not_mutate_the_original_list():
    """원본을 바꿔버리면 재시도 때 쓸 정상 데이터가 오염된다."""
    # Arrange
    items = make_items(3)

    # Act
    collect.inject_defects(items)

    # Assert
    assert len(items) == 3
    assert items[0]["title"] == "제목0"


def test_inject_defects_returns_empty_input_unchanged():
    # Act / Assert
    assert collect.inject_defects([]) == []


# --- 파서 테스트 -------------------------------------------------------------
# 네트워크 대신 합성 HTML을 물려서 CSS 셀렉터 계약을 고정한다.
# 사이트가 마크업을 바꾸면 여기가 먼저 빨간불이 된다.


class FakeResponse:
    """requests.Response 중 파서가 실제로 쓰는 것만 흉내낸다."""

    def __init__(self, text):
        self.text = text
        self.encoding = None

    def raise_for_status(self):
        return None


def sensortower_card(slug, title, meta="Gaming Insights • July 2026"):
    return f"""
    <div class="MuiCard-root has-link">
      <a href="/ko/blog/{slug}"></a>
      <h3>{title}</h3>
      <h4>{meta}</h4>
    </div>
    """


def serve(monkeypatch, html):
    monkeypatch.setattr(collect.requests, "get", lambda *a, **kw: FakeResponse(html))


def test_sensortower_parser_extracts_title_url_and_date(monkeypatch):
    # Arrange
    serve(monkeypatch, sensortower_card("post-1", "제목1"))

    # Act
    items = collect.collect_sensortower()

    # Assert
    assert items == [
        {
            "title": "제목1",
            "url": "https://sensortower.com/ko/blog/post-1",
            "date": "Gaming Insights • July 2026",
            "source": "SensorTower",
        }
    ]


def test_sensortower_parser_skips_cards_without_a_title(monkeypatch):
    """제목 없는 카드가 섞여 들어오면 브리핑에 빈 줄이 생긴다."""
    # Arrange
    serve(monkeypatch, sensortower_card("post-1", "") + sensortower_card("post-2", "제목2"))

    # Act
    items = collect.collect_sensortower()

    # Assert
    assert [i["title"] for i in items] == ["제목2"]


def test_sensortower_parser_caps_results_at_per_source(monkeypatch):
    """브리핑이 한없이 길어지지 않게 소스별 상한을 둔다."""
    # Arrange
    html = "".join(
        sensortower_card(f"post-{i}", f"제목{i}") for i in range(collect.PER_SOURCE + 5)
    )
    serve(monkeypatch, html)

    # Act
    items = collect.collect_sensortower()

    # Assert
    assert len(items) == collect.PER_SOURCE


def test_newzoo_parser_extracts_title_url_and_date(monkeypatch):
    """SOURCES에서 빠져 있어도 함수는 보존 대상이라 계약을 고정해둔다."""
    # Arrange
    serve(
        monkeypatch,
        """
        <div class="article-cell">
          <a href="/articles/post-1"></a>
          <h3 class="case-card-title">제목1</h3>
          <time class="article-meta-date">July 16, 2026</time>
        </div>
        """,
    )

    # Act
    items = collect.collect_newzoo()

    # Assert
    assert items == [
        {
            "title": "제목1",
            "url": "https://newzoo.com/articles/post-1",
            "date": "July 16, 2026",
            "source": "Newzoo",
        }
    ]


def test_collect_aggregates_registered_sources(monkeypatch):
    # Arrange
    monkeypatch.setattr(collect, "SOURCES", (lambda: make_items(2), lambda: make_items(1)))

    # Act
    items = collect.collect()

    # Assert
    assert len(items) == 3


def test_collect_keeps_going_when_one_source_is_blocked(monkeypatch):
    """한 소스가 막혀도 나머지는 수집돼야 한다."""
    # Arrange
    def blocked():
        raise RuntimeError("403 차단")

    monkeypatch.setattr(collect, "SOURCES", (blocked, lambda: make_items(2)))

    # Act
    items = collect.collect()

    # Assert
    assert len(items) == 2
