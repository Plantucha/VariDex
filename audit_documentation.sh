#!/bin/bash
echo "📚 Documentation Audit - Finding What Needs Update"
echo "=================================================="

# Find all .md files
md_files=$(find . -name "*.md" -not -path "./venv/*" -not -path "./.git/*" | sort)

echo ""
echo "Found documentation files:"
for file in $md_files; do
    lines=$(wc -l < "$file")
    modified=$(stat -c %y "$file" 2>/dev/null || stat -f %Sm "$file" 2>/dev/null)
    echo "  $file ($lines lines, modified: ${modified:0:10})"
done

echo ""
echo "=== Checking for Obsolete Content ==="

# Check for old performance claims
echo ""
echo "Files mentioning old/incorrect performance:"
grep -l "slow\|sequential is better\|80 var/s" $md_files 2>/dev/null | while read file; do
    echo "  ⚠️  $file"
    grep -n "slow\|sequential is better\|80 var/s" "$file" | head -3
done

# Check for missing PM2 fix
echo ""
echo "Files needing PM2 fix documentation:"
grep -L "PM2.*fix\|ref_allele.*typo" $md_files 2>/dev/null | head -10

# Check for outdated version numbers
echo ""
echo "Files with version numbers:"
grep -n "v[0-9]\.[0-9]\.[0-9]\|version.*[0-9]" $md_files 2>/dev/null | cut -d: -f1 | sort -u

echo ""
echo "=== Recommended Actions ==="
echo "1. Update performance metrics to 412 var/s"
echo "2. Document PM2 fix"
echo "3. Remove obsolete sequential recommendations"
echo "4. Update version to current"
echo "5. Clean up old troubleshooting docs"
