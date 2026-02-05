#!/usr/bin/env bash
set -euo pipefail

FILE="varidex/core/classifier/__init__.py"

echo "🔧 Patching $FILE ..."

python3 << 'EOF'
from pathlib import Path

path = Path("varidex/core/classifier/__init__.py")
text = path.read_text()

before = text

# Normalize both V7 and V8 blocks:
#  - ensure we use 'err' as the exception variable
#  - ensure the f-string uses {err}
text = text.replace(
    'except ImportError as e:\n'
    '    # V7 requires gnomAD dependencies\n'
    '    def ACMGClassifierV7(*args, **kwargs):\n'
    '        raise ImportError(\n'
    '            "ACMGClassifierV7 requires gnomAD integration. "\n'
    '            "Install with: pip install varidex[gnomad]\\n"\n'
    '            f"Original error: {err}"\n'
    '        )\n',
    'except ImportError as err:\n'
    '    # V7 requires gnomAD dependencies\n'
    '    def ACMGClassifierV7(*args, **kwargs):\n'
    '        raise ImportError(\n'
    '            "ACMGClassifierV7 requires gnomAD integration. "\n'
    '            "Install with: pip install varidex[gnomad]\\n"\n'
    '            f"Original error: {err}"\n'
    '        )\n',
)

text = text.replace(
    'except ImportError as e:\n'
    '    # V8 requires gnomAD + SpliceAI + dbNSFP dependencies\n'
    '    def ACMGClassifierV8(*args, **kwargs):\n'
    '        raise ImportError(\n'
    '            "ACMGClassifierV8 requires gnomAD, SpliceAI, and dbNSFP integration. "\n'
    '            "Install with: pip install varidex[predictions]\\n"\n'
    '            f"Original error: {err}"\n'
    '        )\n',
    'except ImportError as err:\n'
    '    # V8 requires gnomAD + SpliceAI + dbNSFP dependencies\n'
    '    def ACMGClassifierV8(*args, **kwargs):\n'
    '        raise ImportError(\n'
    '            "ACMGClassifierV8 requires gnomAD, SpliceAI, and dbNSFP integration. "\n'
    '            "Install with: pip install varidex[predictions]\\n"\n'
    '            f"Original error: {err}"\n'
    '        )\n',
)

if text == before:
    print("⚠️  No matching patterns were changed (file may already be fixed).")
else:
    path.write_text(text)
    print("✅ Updated exception blocks for V7 and V8 to use 'err' consistently.")
EOF

echo "✅ Done. Verifying with flake8..."
flake8 varidex/core/classifier/__init__.py --select=F821 || true

echo "Next steps:"
echo "  git add varidex/core/classifier/__init__.py"
echo "  git commit --amend --no-edit"
echo "  git push -f origin feature/test-ci"
