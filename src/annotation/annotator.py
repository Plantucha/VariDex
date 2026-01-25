import pandas as pd
from pathlib import Path
from typing import Dict, List
from src.models import NormalizedVariant

class AnnotationDatabase:
    def __init__(self):
        self.scores = {"revel": 0.8, "gnomad_af": 0.01}
    
    def lookup(self, variant):
        return self.scores

class VariantAnnotator:
    def __init__(self):
        self.db = AnnotationDatabase()
    
    def annotate(self, variant):
        return {"revel": 0.8, "status": "annotated"}

class AnnotationPipeline:
    def __init__(self, output_dir):
        self.output_dir = Path(output_dir)
    
    def run(self, variants):
        return len(variants)
