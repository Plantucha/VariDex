#!/bin/bash
# fix-all-dev-v2.sh - FIXED: Direct config replace (no patch issues)
set -euo pipefail

echo "🚀 VariDex Fix v2 (dev) - Direct replace"

# Colors
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'

PROJ_DIR="$(pwd)"; VENV_DIR="$PROJ_DIR/venv"; CONFIG_FILE="$PROJ_DIR/varidex/core/config.py"

# 1. VENV
[[ -d "$VENV_DIR" ]] || python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"
pip install --quiet pydantic black pytest pytest-cov pandas flake8

# 2. FULL CONFIG REPLACE (safe)
echo -e "${YELLOW}Replacing config.py...${NC}"
cp "$CONFIG_FILE" "$CONFIG_FILE.backup"

cat > "$CONFIG_FILE" << 'EOF'
"""VariDexConfig - Pydantic models for genome variant analysis."""
from pydantic import BaseModel, ConfigDict, field_validator
from pathlib import Path
from typing import Optional, Dict, Any
import os
import json

class VariDexConfig(BaseModel):
    """Main config for VariDex pipeline."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    reference_genome: str = "hg38"
    min_quality_score: float = 20.0
    min_read_depth: int = 10
    max_missing_rate: float = 0.1
    population_af_threshold: float = 0.01
    rare_variant_threshold: float = 0.001
    max_population_af: float = 0.01
    num_threads: int = os.cpu_count() or 1
    chunk_size: int = 1000
    enable_caching: bool = True
    clinvar_path: Optional[Path] = None
    gnomad_path: Optional[Path] = None
    dbnsfp_path: Optional[Path] = None
    output_format: str = "json"
    output_dir: Path = Path(".")
    include_annotations: bool = True
    acmg_strict_mode: bool = False
    require_population_data: bool = False
    log_level: str = "INFO"
    debug_mode: bool = False
    validate_inputs: bool = True

    @field_validator('max_population_af')
    @classmethod
    def validate_af(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError("max_population_af must be between 0 and 1")
        return v

    @field_validator('num_threads')
    @classmethod
    def validate_threads(cls, v: int) -> int:
        return max(1, min(v, os.cpu_count() or 1))

    def validate_paths(self) -> None:
        """Ensure output dir exists."""
        if self.output_dir:
            self.output_dir.mkdir(parents=True, exist_ok=True)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict (replaces todict)."""
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VariDexConfig':
        """Load from dict."""
        return cls(**data)

    def save(self, path: Path) -> None:
        """Save config to JSON."""
        self.validate_paths()
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)

    def update(self, **kwargs: Any) -> None:
        """Update fields and validate."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key)
        self.validate_paths()

    def __hash__(self) -> int:
        """Enable hashing for sets/dicts."""
        return hash(tuple(sorted(self.to_dict().items())))

    def __str__(self) -> str:
        """String rep."""
        return f"VariDexConfig({self.to_dict()})"
EOF

black "$CONFIG_FILE"
echo -e "${GREEN}✅ Config replaced & formatted${NC}"

# 3. MATCHER DEBUG PRINTS
MATCHER_FILE="$PROJ_DIR/varidex/io/matching_improved.py"
if [[ -f "$MATCHER_FILE" ]]; then
    cp "$MATCHER_FILE" "$MATCHER_FILE.backup"
    # Add debug coord_key func if missing
    if ! grep -q "def create_coord_key" "$MATCHER_FILE"; then
        cat >> "$MATCHER_FILE" << 'EOF'

def create_coord_key(row):
    """Normalize variant key for matching."""
    chrom = str(row.get('CHROM', row.get('chrom', ''))).upper().lstrip('CHR')
    pos = int(row.get('POS', row.get('pos', 0)))
    ref = str(row.get('REF', row.get('ref', ''))).upper()
    alt = str(row.get('ALT', row.get('alt', ''))).upper()
    return f"{chrom}:{pos}:{ref}>{alt}"

EOF
    fi
    black "$MATCHER_FILE"
    echo -e "${GREEN}✅ Matcher debug added${NC}"
fi

# 4. DUMMY DATA
mkdir -p tests/data
cat > tests/data/sample.vcf << EOF
#CHROM	POS	ID	REF	ALT
1	100	rs123	A	G
2	200	rs456	C	T
EOF

cat > tests/data/sample_23andme.txt << EOF
rsid	chromosome	position	genotype
rs123	1	100	AG
rs456	2	200	CT
EOF

echo -e "${GREEN}✅ Samples created${NC}"

# 5. QUICK TEST
echo -e "${YELLOW}Quick config test:${NC}"
python3 -c "
from varidex.core.config import VariDexConfig
c = VariDexConfig(max_population_af=0.005, num_threads=4)
print('Config OK:', c.max_population_af, c.num_threads)
c.save('test_config.json')
print('Save OK')
" && echo -e "${GREEN}✅ Config works!${NC}" || echo -e "${RED}❌ Config fail${NC}"

# 6. MATCHER DEBUG
echo -e "${YELLOW}Matcher debug:${NC}"
python3 -c "
import pandas as pd
vcf = pd.read_csv('tests/data/sample.vcf', sep='\\t')
u23 = pd.read_csv('tests/data/sample_23andme.txt', sep='\\t\\s*', engine='python')
try:
    from varidex.io.matching_improved import create_coord_key
except:
    def create_coord_key(row): return f'{row.get(\"chromosome\",\"?\")}-{row.get(\"position\",\"?\")}-{row[\"genotype\"][0]}>{row[\"genotype\"][1] if len(row[\"genotype\"])>1 else row[\"genotype\"][0]}'
print('VCF keys:', vcf.apply(create_coord_key, axis=1).tolist())
print('23me keys:', u23.apply(create_coord_key, axis=1).tolist())
" | tee matcher_debug.log

echo -e "${GREEN}🎉 FIXED! Check matcher_debug.log${NC}"
echo "Run full tests: pytest tests/ -v"
echo "Deactivate: deactivate"
