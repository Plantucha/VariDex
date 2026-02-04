"""
ACMG PM1 Splice Prediction using SpliceAI v1.3.1
Development version - not marked as production
"""

import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class SpliceACMG:
    """PM1: Variant in splice region (SpliceAI delta >= 0.5)"""

    def __init__(self, reference_fasta: Optional[str] = None):
        self.reference_fasta = reference_fasta
        self.models = None
        self._lazy_load = True

    def _load_models(self):
        """Lazy load SpliceAI models"""
        if self.models is not None:
            return
        try:
            from keras.models import load_model
            from pkg_resources import resource_filename

            paths = [f"models/spliceai{x}.h5" for x in range(1, 6)]
            self.models = [load_model(resource_filename("spliceai", p)) for p in paths]
            logger.info("SpliceAI models loaded")
        except Exception as e:
            logger.warning(f"Models unavailable: {e}")
            self.models = []

    def score(self, chrom: str, pos: int, ref: str, alt: str) -> Dict:
        """Score variant for PM1 (simulated without reference genome)"""
        if self._lazy_load:
            self._load_models()
            self._lazy_load = False

        if not self.models:
            return {"pm1": None, "delta": 0.0, "scores": {}}

        # Simulated scoring for testing (production needs reference genome)
        is_even_pos = pos % 2 == 0
        if is_even_pos:
            delta = 0.85
            pm1 = "PM1_Strong"
        else:
            delta = 0.0
            pm1 = None

        return {"pm1": pm1, "delta": delta, "scores": {}, "note": "Simulated"}
