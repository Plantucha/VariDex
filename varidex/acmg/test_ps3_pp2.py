#!/usr/bin/env python3
import sys

sys.path.insert(0, "varidex")

from acmg.criteria_PS3_PP2 import PS3PP2Criteria

print("🧪 Testing PS3/PP2 Criteria...")
evaluator = PS3PP2Criteria()

# Test BRCA1 variant
test_gene = "BRCA1"
test_variant = "p.Arg1699Trp"

ps3_result = evaluator.evaluate_ps3(test_gene, test_variant)
print(f"PS3 for {test_gene}:{test_variant} = {ps3_result}")

pp2_metrics = evaluator.evaluate_pp2(test_gene, "missense_variant")
print(f"PP2 metrics: {pp2_metrics}")
