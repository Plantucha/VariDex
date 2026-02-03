# Secret Scanning Setup Guide

## Overview

Detect-secrets is a security tool that scans your codebase for accidentally committed secrets (API keys, passwords, tokens) before they reach production[web:27]. VariDex uses it in CI/CD to prevent security leaks.

## Installation

### Local Development Setup

```bash
# Install detect-secrets
pip install detect-secrets

# Verify installation
detect-secrets --version
```

### CI/CD Integration

Detect-secrets already runs in GitHub Actions[cite:17]:

```yaml
secret-scan:
  name: Secret Scanning
  runs-on: ubuntu-latest
  
  steps:
  - name: Checkout repository
    uses: actions/checkout@v4
    with:
      fetch-depth: 0  # Full history for better detection
  
  - name: Install detect-secrets
    run: |
      pip install detect-secrets
  
  - name: Run detect-secrets
    run: |
      detect-secrets scan --all-files --force-use-all-plugins > .secrets.baseline || true
```

## Initial Setup

### 1. Create Baseline File

Generate a baseline of existing "secrets" in your codebase:

```bash
# Scan and create baseline
detect-secrets scan --all-files --force-use-all-plugins > .secrets.baseline

# The baseline file captures current state
# Any new secrets will be flagged as violations
```

### 2. Review and Audit Baseline

Review detected secrets and mark false positives:

```bash
# Audit the baseline interactively
detect-secrets audit .secrets.baseline

# For each detected secret:
# - Press 'y' if it's a real secret (should be removed)
# - Press 'n' if it's a false positive (test data, example, etc.)
# - Press 's' to skip
```

### 3. Add to Version Control

```bash
# Add the audited baseline to git
git add .secrets.baseline
git commit -m "security: Add detect-secrets baseline"
```

## Configuration

### Create `.secrets.toml` Configuration

Customize detection behavior:

```toml
# .secrets.toml
[tool.detect-secrets]
version = "1.4.0"

# Plugins to use
plugins_used = [
  { name = "ArtifactoryDetector" },
  { name = "AWSKeyDetector" },
  { name = "AzureStorageKeyDetector" },
  { name = "BasicAuthDetector" },
  { name = "CloudantDetector" },
  { name = "DiscordBotTokenDetector" },
  { name = "GitHubTokenDetector" },
  { name = "PrivateKeyDetector" },
  { name = "SlackDetector" },
  { name = "SoftlayerDetector" },
  { name = "StripeDetector" },
  { name = "TwilioKeyDetector" },
]

# Files to exclude
exclude_files = [
  "package-lock.json",
  "poetry.lock",
  "go.sum",
  ".secrets.baseline",
  "tests/fixtures/.*",
]

# Patterns to ignore
[filters]
exclude_lines = [
  "^\\s*#",  # Comments
  "password\\s*=\\s*['\"](?:your|test|example|sample)['\"]"  # Test passwords
]
```

### Common Exclusions for Genomics Projects

```toml
# Additional exclusions for VariDex
exclude_files = [
  # Data files
  "*.vcf",
  "*.vcf.gz",
  "*.bed",
  "*.fasta",
  "*.fastq",
  
  # Test data
  "tests/fixtures/.*",
  "tests/data/.*",
  "examples/.*",
  
  # Documentation
  "docs/.*\.md",
  "*.rst",
  
  # Build/dependencies
  "dist/.*",
  "build/.*",
  "*.egg-info/.*",
  "requirements*.txt",
]
```

## Usage

### Scan for New Secrets

```bash
# Scan all files and compare to baseline
detect-secrets scan --baseline .secrets.baseline

# Scan specific directory
detect-secrets scan varidex/ --baseline .secrets.baseline

# Update baseline with new files
detect-secrets scan --update .secrets.baseline
```

### Audit Workflow

```bash
# 1. Scan for new secrets
detect-secrets scan --baseline .secrets.baseline

# 2. If new secrets found, audit them
detect-secrets audit .secrets.baseline

# 3. Review and mark false positives
# Press 'y' for real secrets, 'n' for false positives

# 4. Remove real secrets from code
# Replace with environment variables or config

# 5. Update baseline
detect-secrets scan --update .secrets.baseline
```

### Check Specific Files

```bash
# Check before committing
detect-secrets scan varidex/integrations/gnomad_client.py

# Check changed files only
git diff --name-only | xargs detect-secrets scan --baseline .secrets.baseline
```

## Pre-commit Hook (Recommended)

Automate secret scanning before each commit:

### 1. Install pre-commit

```bash
pip install pre-commit
```

### 2. Create `.pre-commit-config.yaml`

```yaml
repos:
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.4.0
    hooks:
      - id: detect-secrets
        args: ['--baseline', '.secrets.baseline']
        exclude: |
          (?x)^(
            package-lock.json|
            poetry.lock|
            tests/fixtures/.*|
            .*\.vcf|
            .*\.vcf\.gz
          )$
```

### 3. Install the hook

```bash
# Install pre-commit hook
pre-commit install

# Test it
pre-commit run --all-files
```

Now detect-secrets runs automatically on `git commit`!

## Handling False Positives

### Method 1: Inline Pragma

Add comment to suppress specific line:

```python
# This is a test API key, not a real secret
TEST_API_KEY = "sk-test-abcdefgh1234567890"  # pragma: allowlist secret
```

### Method 2: Update Baseline

Mark as false positive in baseline:

```bash
# Audit and mark false positives
detect-secrets audit .secrets.baseline

# Press 'n' for false positives
```

### Method 3: Exclude Pattern

Add to `.secrets.toml`:

```toml
[filters]
exclude_lines = [
  "TEST_.*_KEY",  # Test keys
  "EXAMPLE_.*",   # Example values
  "sk-test-.*",   # Stripe test keys
]
```

### Common False Positives in Genomics Code

```python
# Chromosome coordinates may trigger detection
chrom_position = "chr17:41234567"  # pragma: allowlist secret

# Gene symbols with numbers
gene_symbol = "BRCA1p.Arg1751Ter"  # pragma: allowlist secret

# RefSeq accessions
refseq_id = "NM_007294.3"  # pragma: allowlist secret

# gnomAD variant IDs
variant_id = "17-41234567-G-A"  # pragma: allowlist secret
```

## Security Best Practices

### 1. Never Commit Real Secrets

**Instead of:**
```python
# DON'T DO THIS!
API_KEY = "sk-live-abc123xyz789"
```

**Use environment variables:**
```python
import os

API_KEY = os.environ.get("GNOMAD_API_KEY")
if not API_KEY:
    raise ValueError("GNOMAD_API_KEY environment variable not set")
```

### 2. Use Configuration Files

**Create `.env` file (add to `.gitignore`):**
```bash
# .env (NOT committed to git)
GNOMAD_API_KEY=your_actual_key_here
CLINVAR_API_TOKEN=your_token_here
```

**Load in code:**
```python
from dotenv import load_dotenv
import os

load_dotenv()  # Load from .env file
api_key = os.environ["GNOMAD_API_KEY"]
```

### 3. Separate Test Credentials

```python
# config.py
class Config:
    """Application configuration."""
    
    def __init__(self):
        self.api_key = os.environ.get("API_KEY")
        self.is_test = os.environ.get("TESTING", "false").lower() == "true"
    
    @property
    def effective_api_key(self) -> str:
        if self.is_test:
            return "test-key-12345"  # pragma: allowlist secret
        return self.api_key
```

### 4. Document Secrets in README

Create `SECRETS.md`:

```markdown
# Required Secrets/API Keys

## Development
- `GNOMAD_API_KEY`: gnomAD API access (optional)
- `CLINVAR_API_TOKEN`: ClinVar API token (optional)

## CI/CD (GitHub Secrets)
- `CODECOV_TOKEN`: Code coverage upload
- `PYPI_API_TOKEN`: Package publishing

## How to Obtain
1. gnomAD API: Register at https://gnomad.broadinstitute.org/
2. ClinVar: Public API, no key required
```

## CI/CD Configuration

### GitHub Actions Current Setup

The security workflow is non-blocking[cite:17]:

```yaml
- name: Run detect-secrets
  run: |
    detect-secrets scan --all-files --force-use-all-plugins > .secrets.baseline || true

- name: Check for secrets
  run: |
    if [ -s .secrets.baseline ]; then
      echo "⚠️ Potential secrets detected!"
      cat .secrets.baseline
      # Don't fail the build, but warn
    else
      echo "✅ No secrets detected"
    fi
```

### Enable Blocking Mode (Future)

Once baseline is clean, enforce secret scanning:

```yaml
- name: Run detect-secrets
  run: |
    detect-secrets scan --all-files --force-use-all-plugins --baseline .secrets.baseline
    # Fails if new secrets detected
```

## Troubleshooting

### Issue: Too Many False Positives

**Solution:** Tune the configuration

```bash
# Create a custom plugins list
detect-secrets scan --list-all-plugins

# Disable specific plugins
detect-secrets scan --disable-plugin KeywordDetector
```

### Issue: Large Files Cause Slow Scans

**Solution:** Exclude data directories

```toml
exclude_files = [
  "data/.*",
  "*.vcf",
  "*.vcf.gz",
  "*.bam",
]
```

### Issue: Can't Audit Baseline

**Solution:** Check baseline format

```bash
# Validate baseline JSON
python -m json.tool .secrets.baseline > /dev/null

# Regenerate if corrupt
detect-secrets scan --all-files --force-use-all-plugins > .secrets.baseline
```

### Issue: Pre-commit Hook Blocks Valid Commits

**Solution:** Temporarily bypass

```bash
# Skip pre-commit hooks (use sparingly!)
git commit --no-verify -m "message"

# Or fix the false positive
detect-secrets audit .secrets.baseline
```

## Monitoring and Reporting

### Generate Reports

```bash
# JSON report
detect-secrets scan --all-files > secrets-report.json

# Summary statistics
cat secrets-report.json | jq '.results | length'

# List detected secret types
cat secrets-report.json | jq '.plugins_used[].name'
```

### GitHub Actions Artifacts

Security reports are uploaded automatically[cite:17]:

```yaml
- name: Upload security reports
  uses: actions/upload-artifact@v4
  if: always()
  with:
    name: security-reports
    path: |
      safety-report.json
      bandit-report.json
    retention-days: 90
```

Access at: Actions → Workflow Run → Artifacts

## Migration Guide

### If You Find Real Secrets

**1. Rotate immediately:**
```bash
# Revoke the exposed credential
# Generate new credential
# Update in secure location (GitHub Secrets, env vars)
```

**2. Remove from git history:**
```bash
# Use BFG Repo Cleaner or git filter-branch
bfg --replace-text passwords.txt

# Or for single file
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch path/to/secret.py" \
  --prune-empty --tag-name-filter cat -- --all
```

**3. Force push (coordinate with team):**
```bash
git push --force --all
git push --force --tags
```

## Resources

- [detect-secrets Documentation](https://github.com/Yelp/detect-secrets)
- [IBM detect-secrets Guide](https://cloud.ibm.com/docs/devsecops?topic=devsecops-cd-devsecops-detect-secrets-scans)[web:27]
- [OWASP Secret Management](https://owasp.org/www-community/vulnerabilities/Use_of_hard-coded_password)
- [GitHub Secret Scanning](https://docs.github.com/en/code-security/secret-scanning)

## Support

For secret scanning questions:
1. Check this guide first
2. Review [detect-secrets docs](https://github.com/Yelp/detect-secrets)
3. Ask in project discussions with `[security]` tag
4. Report security issues privately to plantucha@gmail.com

---

**Version:** 7.0.3-dev  
**Last Updated:** February 2026
