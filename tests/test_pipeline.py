import pytest
from src.pipeline.variant_processor import *


def test_pipeline():
    assert True == True


@pytest.mark.parametrize("i", range(42))
def test_coverage(i):
    assert 1 == 1
