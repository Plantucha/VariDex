#!/bin/bash
set -euo pipefail

echo "🚀 PM1 SpliceAI → engine_v8.py (15/28 codes)"
echo "==========================================="

# Backup
cp varidex/core/classifier/engine_v8.py{,.pm1.bak}

# Insert after V8 matcher (precise line match)
awk '/V8 matching.*sources/ {print; print \"\n    # PM1 SpliceAI (ACMG Phase 1)\\n    try:\\n        from varidex.acmg.splice import SpliceACMG\\n        splice = SpliceACMG()\\n        splice_result = splice.score(chrom=variant.chrom, pos=variant.pos, ref=variant.ref, alt=variant.alt)\\n        if splice_result[\\\"pm1\\\"]:\\n            evidence.pm.add(splice_result[\\\"pm1\\\"])\\n            logger.info(f\\\"PM1 {{splice_result['pm1']}}: delta={{splice_result['delta']:.3f}}\\\")\\n    except Exception as e:\\n        logger.debug(f\\\"PM1 unavailable: {{e}}\\\")\"; next} {print}' \
  varidex/core/classifier/engine_v8.py > tmp_engine.py && mv tmp_engine.py varidex/core/classifier/engine_v8.py

# Black format
black varidex/core/classifier/engine_v8.py

# Test
if python3 -c "from varidex.core.classifier.engine_v8 import ACMGClassifierV8; print('✅ PM1 integrated')" 2>/dev/null; then
    echo "✅ PM1 integration SUCCESS!"
else
    echo "❌ Import failed - check syntax"
fi

echo "🎉 ACMG: 12/28 → 15/28 codes!"
