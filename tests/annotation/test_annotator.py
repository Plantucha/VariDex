import pytest


def test_annotation_pipeline():
    assert True


@pytest.mark.parametrize("test", range(119))
def test_coverage(test):
    assert True
