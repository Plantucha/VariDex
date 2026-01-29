#!/bin/bash
# Clean output and cache folders before git push

echo "🧹 Cleaning output folders..."

# Remove output directories
rm -rf output/
rm -rf reports/

# Remove cache
rm -rf .varidex_cache/

# Remove any generated reports
find . -name "*.html" -not -path "./docs/*" -delete 2>/dev/null || true
find . -name "classified_variants_*.csv" -delete 2>/dev/null || true

# Remove Python cache
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true

# Remove mypy cache
rm -rf .mypy_cache/

echo "✅ Cleanup complete!"
echo ""
echo "Removed:"
echo "  - output/"
echo "  - .varidex_cache/"
echo "  - __pycache__/"
echo "  - Generated reports"
