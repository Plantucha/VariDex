#!/bin/bash
# VariDex Code Formatter
# Applies Black formatting to all Python files

echo "🎨 Formatting with Black (line-length=88)..."
black varidex/ --line-length 88

echo ""
echo "✅ All files formatted!"
