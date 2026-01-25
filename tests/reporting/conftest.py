import pytest
from src.reporting.models import AnnotatedVariant

@pytest.fixture(scope="module")
def sample_variants():
    return [
        AnnotatedVariant(chr="1", pos=100, ref="A", alt="T", acmg_class="P", gnomad_af=0.01),
        AnnotatedVariant(chr="2", pos=200, ref="C", alt="G", acmg_class="B", gnomad_af=0.05),
    ]
