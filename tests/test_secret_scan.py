from scripts.scan_repository_secrets import scan


def test_repository_contains_no_recognizable_credentials():
    assert scan() == []
