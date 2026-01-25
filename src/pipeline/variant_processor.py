from dataclasses import dataclass, field
from typing import List, Optional
from varidex.exceptions import ValidationError
from .stages import ValidationStage, AnnotationStage, FilteringStage, OutputStage

@dataclass
class PipelineConfig:
    input_vcf: Optional[str] = None
    output_dir: str = "output" 
    stages: List[str] = field(default_factory=list)
    continue_on_error: bool = False
    
    def __init__(self, input_vcf: Optional[str] = None,
                 output_dir: str = "output",
                 stages: Optional[List[str]] = None,
                 continue_on_error: bool = False):
        self.input_vcf = input_vcf
        self.output_dir = output_dir
        self.stages = stages or []
        self.continue_on_error = continue_on_error

class PipelineOrchestrator:
    def __init__(self, config: PipelineConfig):
        self.config = config
    
    def run_pipeline(self):
        return True
