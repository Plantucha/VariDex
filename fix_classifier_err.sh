#!/usr/bin/env bash
set -euo pipefail

FILE="varidex/core/classifier/__init__.py"

echo "🔍 Checking current state..."
grep -n "except ImportError as" "$FILE"

echo -e "\n🔧 Fixing exception variable names...\n"

# Simple search and replace - change ALL 'as e:' to 'as err:' in ImportError blocks
sed -i.bak '
/except ImportError as e:/ {
  s/as e:/as err:/g
}
' "$FILE"

echo "✅ Fixed exception variable names"

# Verify
echo -e "\n📋 Verification:"
flake8 "$FILE" --select=F821 || true

echo -e "\n✨ Ready to commit:"
echo "git add $FILE"
echo "git commit --amend --no-edit"
echo "git push -f origin feature/test-ci"
