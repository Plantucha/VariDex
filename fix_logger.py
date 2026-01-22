with open('varidex/core/classifier/acmg_evidence_pathogenic.py', 'r') as f:
    lines = f.readlines()

# Replace broken logger.info (lines 97-105)
lines[96] = '        logger.info(f"PathogenicEvidenceAssigner initialized")\n'
del lines[97:105]  # Remove broken lines

with open('varidex/core/classifier/acmg_evidence_pathogenic.py', 'w') as f:
    f.writelines(lines)
print("✅ Fixed logger.info syntax")
