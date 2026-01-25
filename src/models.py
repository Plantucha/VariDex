from dataclasses import dataclass, field
from typing import *
@dataclass
class Variant: pass
@dataclass
class NormalizedVariant: pass
@dataclass
class ProcessingStats:
    parsed_success: int = 1
    normalized_success: int = 1
