"""
tests/fixtures/stubs.py - Test Compatibility Stubs v1.0.0-dev

Stub implementations for test compatibility.

Development version - not for production use.
"""

from typing import List, Any, Optional, Dict


class PipelineOrchestrator:
    """Stub pipeline orchestrator for test compatibility."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize orchestrator."""
        self.config = config or {}
        self.stages: List[Any] = []

    def add_stage(self, stage: Any) -> None:
        """Add a pipeline stage."""
        self.stages.append(stage)

    def run(self, input_data: Any) -> Any:
        """Execute all pipeline stages."""
        result = input_data
        for stage in self.stages:
            if hasattr(stage, "execute"):
                result = stage.execute(result)
        return result
