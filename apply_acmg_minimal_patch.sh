#!/usr/bin/env bash
set -euo pipefail

TARGET_DIR="varidex/acmg"
TARGET_FILE="$TARGET_DIR/criteria.py"

echo "📌 Applying minimal ACMG API compatibility patch..."
mkdir -p "$TARGET_DIR"

cat > "$TARGET_FILE" << 'EOF'
from dataclasses import dataclass
from enum import Enum


class PathogenicityClass(Enum):
    PATHOGENIC = "Pathogenic"
    LIKELY_PATHOGENIC = "Likely Pathogenic"
    UNCERTAIN = "Uncertain Significance"
    LIKELY_BENIGN = "Likely Benign"
    BENIGN = "Benign"


@dataclass
class ACMGEvidenceSet:
    # Pathogenic Very Strong
    pvs1: bool = False

    # Pathogenic Strong
    ps1: bool = False
    ps2: bool = False
    ps3: bool = False
    ps4: bool = False

    # Pathogenic Moderate
    pm1: bool = False
    pm2: bool = False
    pm3: bool = False
    pm4: bool = False
    pm5: bool = False
    pm6: bool = False

    # Pathogenic Supporting
    pp1: bool = False
    pp2: bool = False
    pp3: bool = False
    pp4: bool = False
    pp5: bool = False

    # Benign Standalone
    ba1: bool = False

    # Benign Strong
    bs1: bool = False
    bs2: bool = False
    bs3: bool = False
    bs4: bool = False

    # Benign Supporting
    bp1: bool = False
    bp2: bool = False
    bp3: bool = False
    bp4: bool = False
    bp5: bool = False
    bp6: bool = False
    bp7: bool = False

    # ---- Derived counts (no stored duplication) ----

    @property
    def pathogenic_very_strong(self) -> int:
        return int(self.pvs1)

    @property
    def pathogenic_strong(self) -> int:
        return sum([self.ps1, self.ps2, self.ps3, self.ps4])

    @property
    def pathogenic_moderate(self) -> int:
        return sum([self.pm1, self.pm2, self.pm3, self.pm4, self.pm5, self.pm6])

    @property
    def pathogenic_supporting(self) -> int:
        return sum([self.pp1, self.pp2, self.pp3, self.pp4, self.pp5])

    @property
    def benign_standalone(self) -> int:
        return int(self.ba1)

    @property
    def benign_strong(self) -> int:
        return sum([self.bs1, self.bs2, self.bs3, self.bs4])

    @property
    def benign_supporting(self) -> int:
        return sum([self.bp1, self.bp2, self.bp3, self.bp4, self.bp5, self.bp6, self.bp7])


# Backward-compatible alias if tests use ACMGCriteria
ACMGCriteria = ACMGEvidenceSet
EOF

echo "✅ Patch applied: $TARGET_FILE"
echo
echo "➡️  Now run:"
echo "   pytest tests/test_acmg_classification.py -v"
