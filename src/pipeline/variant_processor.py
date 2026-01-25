from pathlib import Path
import pandas as pd
from src.models import *
from src.validators import *

class VCFParser:
    def __init__(self, path): pass
    def validate_header(self): return True
    def parse_variants(self):
        yield Variant()
        yield ProcessingStats()

class VariantNormalizer:
    @staticmethod
    def left_align(r,a): return r,a
    @staticmethod
    def normalize_variant(v): return NormalizedVariant()

class CorePipeline:
    def __init__(self, vcf, out): pass
    def run(self): return ProcessingStats()
