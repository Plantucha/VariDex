#!/bin/bash
# refresh_installation.sh - Clear cache and reinstall VariDex

set -e

echo "======================================================================"
echo "VARIDEX INSTALLATION REFRESH"
echo "======================================================================"
echo ""

# Step 1: Clear Python cache
echo "[1/4] 🧹 Clearing Python cache..."
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
find . -type f -name '*.pyc' -delete 2>/dev/null || true
find . -type f -name '*.pyo' -delete 2>/dev/null || true
echo "  ✓ Cache cleared"
echo ""

# Step 2: Uninstall existing package
echo "[2/4] 🗑️  Uninstalling existing VariDex..."
pip uninstall -y varidex 2>/dev/null || echo "  (not installed)"
echo "  ✓ Uninstalled"
echo ""

# Step 3: Reinstall in development mode
echo "[3/4] 📦 Installing VariDex in development mode..."
pip install -e . --no-cache-dir
echo "  ✓ Installed"
echo ""

# Step 4: Verify installation
echo "[4/4] ✅ Verifying installation..."
python3 -c "import varidex; print(f'  ✓ VariDex version: {varidex.__version__}')"
python3 -c "from varidex.io.normalization import _get_available_memory_gb; mem=_get_available_memory_gb(); print(f'  ✓ Memory detection: {mem:.1f}GB available')"
echo ""

echo "======================================================================"
echo "✅ INSTALLATION REFRESHED"
echo "======================================================================"
echo ""
echo "You can now run your pipeline:"
echo ""
echo "  python3 -m varidex.pipeline.orchestrator \\"
echo "      clinvar/clinvar_GRCh37.vcf.gz \\"
echo "      data/rawM.txt \\"
echo "      --format 23andme"
echo ""
