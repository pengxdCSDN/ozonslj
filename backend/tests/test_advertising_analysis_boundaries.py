import math

import pytest

from backend.app.domain.advertising_analysis import analyze_advertising


def test_advertising_analysis_rejects_boolean_metric_and_infinite_threshold() -> None:
    with pytest.raises(ValueError):
        analyze_advertising(
            spend_minor=True, ad_sales_minor=1, total_sales_minor=1,
            keyword_count=1, unconverted_keyword_count=0, acos_alert_percent=20,
        )
    with pytest.raises(ValueError):
        analyze_advertising(
            spend_minor=1, ad_sales_minor=1, total_sales_minor=1,
            keyword_count=1, unconverted_keyword_count=0, acos_alert_percent=math.inf,
        )
