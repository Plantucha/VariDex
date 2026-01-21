# VariDex v6.0.0 Security Fixes

**Document Version:** 1.0  
**Last Updated:** 2026-01-19  
**Priority:** CRITICAL

Security vulnerabilities discovered and fixed in v6.0.0 migration.

---

## CVE-Level Vulnerabilities

### 1. XSS in HTML Reports (CRITICAL)

**Location:** file_6a_generator.txt, file_6B_templates.txt

**Vulnerability:**
```python
# VULNERABLE CODE (v5.2):
def generate_variant_table(variants):
    html = "<table>"
    for variant in variants:
        html += f"<td>{variant.gene}</td>"  # NO ESCAPING!
    return html

# Attack vector:
variant.gene = "<script>alert('XSS')</script>"
# Result: JavaScript executed in user's browser
```

**Fix:**
```python
# SECURE CODE (v6.0.0):
import html

def generate_variant_table(variants):
    html_parts = ["<table>"]
    for variant in variants:
        safe_gene = html.escape(str(variant.gene))
        html_parts.append(f"<td>{safe_gene}</td>")
    return "".join(html_parts)

# Attack blocked:
# Input:  <script>alert('XSS')</script>
# Output: &lt;script&gt;alert('XSS')&lt;/script&gt;
```

**Files to Update:**
- `reports/templates/builder.py`: Escape all variables
- `reports/templates/components.py`: Escape all variables
- `reports/formatters.py`: Escape HTML report data

---

### 2. CSV Formula Injection (HIGH)

**Location:** file_6a_generator.txt

**Vulnerability:**
```python
# VULNERABLE CODE:
df.to_csv("output.csv")  # No sanitization

# Attack vector:
variant.gene = "=1+1"  # Excel executes as formula
variant.gene = "=cmd|'/c calc'"  # Can execute commands!
```

**Fix:**
```python
# SECURE CODE (v6.0.0):
def sanitize_csv_value(value):
    """Prevent CSV formula injection."""
    value = str(value)
    if value.startswith(('=', '+', '-', '@', '\t', '\r')):
        return "'" + value  # Prefix with quote to force text
    return value

def generate_csv_report(df, output_file):
    # Sanitize all string columns
    for col in df.select_dtypes(include=['object']).columns:
        df[col] = df[col].apply(sanitize_csv_value)

    df.to_csv(output_file, index=False, quoting=csv.QUOTE_NONNUMERIC)
```

---

### 3. Path Traversal (MEDIUM)

**Location:** file_0_downloader.txt, file_5_loader.txt

**Vulnerability:**
```python
# VULNERABLE CODE:
def load_file(user_filename):
    path = Path(user_filename)  # No validation!
    return pd.read_csv(path)

# Attack vector:
load_file("../../etc/passwd")  # Access system files!
```

**Fix:**
```python
# SECURE CODE (v6.0.0):
def validate_file_path(filepath, allowed_dir):
    """Prevent path traversal attacks."""
    filepath = Path(filepath).resolve()
    allowed_dir = Path(allowed_dir).resolve()

    if not filepath.is_relative_to(allowed_dir):
        raise SecurityError(f"Path outside allowed directory")

    return filepath
```

---

## Security Testing Requirements

### Test 1: XSS Prevention

```python
def test_xss_prevention():
    xss_payloads = [
        "<script>alert('XSS')</script>",
        "<img src=x onerror=alert(1)>",
    ]

    for payload in xss_payloads:
        variant = VariantData(gene=payload)
        html = generate_variant_table([variant])

        assert "<script>" not in html
        assert "&lt;script&gt;" in html
```

### Test 2: CSV Injection Prevention

```python
def test_csv_formula_injection():
    dangerous = ["=1+1", "=cmd|'/c calc'", "@SUM(A1:A10)"]

    for value in dangerous:
        df = pd.DataFrame({"gene": [value]})
        csv_output = generate_csv_report(df)

        assert csv_output.startswith("'")
```

### Test 3: Path Traversal Prevention

```python
def test_path_traversal():
    attacks = ["../../etc/passwd", "/etc/passwd"]

    for attack in attacks:
        with pytest.raises(SecurityError):
            validate_file_path(attack, "/allowed/dir")
```

---

## Security Checklist

**Before Deployment:**
- [ ] All HTML output uses `html.escape()`
- [ ] CSV generation sanitizes formulas
- [ ] File paths validated against traversal
- [ ] No pickle usage (replaced with Parquet)
- [ ] All inputs validated (chromosomes, positions, rsIDs)
- [ ] Security tests pass (100% coverage on attack vectors)

---

See also:
- `02_file_splits.md`: File restructuring for security
- `05_testing_deployment.md`: Security test execution
