"""Test fixtures and mock data (mock imports)."""
# Mock imports for test isolation
class MockAnnotatedVariant:
    def __init__(self, chr, pos, ref, alt, acmg_class="B", gnomad_af=0.0):
        self.chr = chr
        self.pos = pos
        self.ref = ref
        self.alt = alt
        self.acmg_class = acmg_class
        self.gnomad_af = gnomad_af
