#!/bin/bash
# Commit v7.0.3 with proper message escaping

# Stage changes
git add .gitignore
git add mypy.ini
git add pyproject.toml
git add requirements.txt
git add requirements-dev.txt
git add RELEASE_NOTES_v7.0.3.md
git add format_code.sh
git add pre_push_check.sh
git add clean_before_push.sh
git add varidex/

# Commit with multiline message
git commit -m "Release v7.0.3: Performance optimization with intelligent caching" \
           -m "" \
           -m "Features:" \
           -m "- Intelligent ClinVar caching with auto-invalidation (56x speedup)" \
           -m "- PyArrow-based Parquet compression (4.3M variants → 230MB)" \
           -m "- Cache loads in 0.7s vs 225s full parse" \
           -m "" \
           -m "Improvements:" \
           -m "- Added pyarrow>=23.0.0 dependency" \
           -m "- Black-formatted all code (88 char line length)" \
           -m "- Development-friendly mypy configuration" \
           -m "- Updated pyproject.toml to v7.0.3" \
           -m "" \
           -m "Performance:" \
           -m "- First run: 3m 45s (creates cache)" \
           -m "- Cached run: 4s (56x faster)"

echo ""
echo "✅ Committed successfully!"
echo ""
echo "Run: git push origin main"
