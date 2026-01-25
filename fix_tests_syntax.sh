#!/bin/bash
set -e

for file in tests/test_pipeline_orchestrator.py tests/test_pipeline_stages.py; do
    # Add missing imports at top
    sed -i '1iimport pytest\nfrom unittest.mock import Mock, patch' "$file"
    
    # Fix malformed @patch (replace invalid lines)
    sed -i 's/@patch("src.pipeline.stages.*)/@patch("src.pipeline.stages.ValidationStage")/g' "$file"
    sed -i 's/@patch("src.annotation.*)/@patch("src.pipeline.stages.AnnotationStage")/g' "$file"
done

echo "✅ Test syntax fixed"
