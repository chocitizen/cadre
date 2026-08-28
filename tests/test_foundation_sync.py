from scripts.validate_foundation_sync import validate


def test_canonical_foundation_package_and_registry_are_intact():
    assert validate() == []
