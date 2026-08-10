import pytest

from backend.app.domain.data_source import get_data_source_label


def test_data_source_labels_distinguish_estimates() -> None:
    assert get_data_source_label("official_private").estimated is False
    assert get_data_source_label("public_sample").estimated is True
    assert get_data_source_label("derived_estimate").label == "推导估算"


def test_unknown_data_source_is_rejected() -> None:
    with pytest.raises(ValueError, match="来源"):
        get_data_source_label("unknown")
