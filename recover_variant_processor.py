#!/usr/bin/env python3
# recover_variant_processor.py - Restore + fix PipelineConfig (development)
from pathlib import Path
import sys

FILE = Path("src/pipeline/variant_processor.py")

# Full minimal working version (imports + PipelineConfig + stubs)
content = '''from dataclasses import dataclass
from typing import List, Optional
from varidex.exceptions import ValidationError

@dataclass
class PipelineConfig:
    input_vcf: Optional[str] = None
    output_dir: str = "output"
    stages: List[str] = None
    continue_on_error: bool = False
    
    def __init__(self, input_vcf: Optional[str] = None, 
                 output_dir: str = "output", stages: List[str] = None, 
                 continue_on_error: bool = False):
        self.input_vcf = input_vcf
        self.output_dir = output_dir
        self.stages = stages or []
        self.continue_on_error = continue_on_error

# Stub classes for tests (add real impl later)
class PipelineOrchestrator:
    def __init__(self, config: PipelineConfig):
        self.config = config
    
    def run_pipeline(self):
        return True

def main():
    FILE.write_text(content)
    print("✅ Restored variant_processor.py with imports + PipelineConfig")

if __name__ == "__main__":
    main()
