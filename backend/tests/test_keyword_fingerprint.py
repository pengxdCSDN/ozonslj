from backend.app.domain.keyword_import import keyword_import_bytes_fingerprint


def test_binary_fingerprint_is_stable_and_distinguishes_files() -> None:
    assert keyword_import_bytes_fingerprint(b"xlsx") == keyword_import_bytes_fingerprint(b"xlsx")
    assert keyword_import_bytes_fingerprint(b"xlsx") != keyword_import_bytes_fingerprint(b"other")
