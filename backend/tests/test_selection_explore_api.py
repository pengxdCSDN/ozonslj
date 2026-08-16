from fastapi.testclient import TestClient

from backend.app.main import create_app


def test_explore_api_returns_ranked_estimated_opportunities() -> None:
    response = TestClient(create_app()).post(
        "/v1/selection/explore/run",
        json={
            "items": [
                {"keyword": "термос", "search_count": 1000, "sample_count": 5, "own_stock": 0}
            ]
        },
    )
    assert response.status_code == 200
    assert response.json()[0]["estimated"] is True
    assert response.json()[0]["own_coverage_gap"] is True


def test_explore_api_applies_candidate_filters_before_returning() -> None:
    response = TestClient(create_app()).post(
        "/v1/selection/explore/run",
        json={
            "items": [
                {"keyword": "термос", "search_count": 1000, "conversion_rate": 12, "own_stock": 0},
                {"keyword": "чехол", "search_count": 500, "conversion_rate": 5, "own_stock": 10},
            ],
            "min_search_count": 900,
            "coverage_gap_only": True,
        },
    )
    assert response.status_code == 200
    assert [item["keyword"] for item in response.json()] == ["термос"]
