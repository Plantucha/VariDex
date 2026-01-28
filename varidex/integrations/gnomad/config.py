"""
varidex/integrations/gnomad/config.py v6.4.0-dev

Configuration for gnomAD integration.

Development version - not for production use.
"""

from dataclasses import dataclass
from pathlib import Path


@dataclass
class GnomADConfig:
    enabled: bool = True
    gnomad_dir: Path = Path("gnomad")
    build: str = "GRCh37"
    BA1_threshold: float = 0.05
    BS1_threshold: float = 0.01
    PM2_threshold: float = 0.0001

    def __post_init__(self):
        self.gnomad_dir = Path(self.gnomad_dir)
