#!/usr/bin/env python3
"""
varidex/reports/templates/builder.py - HTML Template Builder v6.0.0
Generates secure HTML reports with CSP Level 3 and XSS protection.

VERSION: 6.0.0 | AUTHOR: VariDex Team
"""

import os
import secrets
import html
from datetime import datetime
from typing import Dict, Optional

try:
    from varidex.version import __version__
except ImportError:
    __version__ = '6.0.0'

from varidex.reports.templates.components import (
    build_stats_dashboard,
    build_classification_legend,
    build_truncation_warning
)

__all__ = ['generate_html_template', 'generate_minimal_template']


def _generate_nonce() -> str:
    """Generate cryptographically secure nonce for CSP."""
    return secrets.token_urlsafe(16)


def _validate_css_path(css_file: str) -> str:
    """Validate CSS path to prevent directory traversal."""
    safe = os.path.basename(css_file)
    return safe if all(c.isalnum() or c in '.-_' for c in safe) else "styles.css"


def _validate_custom_code(code: Optional[str], code_type: str, max_len: int = 10000) -> str:
    """Validate custom CSS/JS to prevent abuse."""
    if not code:
        return ""
    code = code[:max_len] if len(code) > max_len else code
    bad = ['</style>', '</script>', 'javascript:', 'onerror=', 'onload=']
    return "" if any(p in code.lower() for p in bad) else code


def _validate_stats(stats: Dict[str, int]) -> Dict[str, int]:
    """Validate stats dictionary."""
    keys = ['total', 'pathogenic', 'likely_pathogenic', 'vus', 'likely_benign', 'benign', 'conflicts']
    validated = {}
    for k in keys:
        try:
            validated[k] = int(stats.get(k, 0))
        except (ValueError, TypeError):
            validated[k] = 0
    return validated


def generate_html_template(
    stats: Dict[str, int],
    table_rows: str,
    is_truncated: bool,
    total_significant: int,
    html_max_variants: int,
    output_filename: str,
    custom_css: Optional[str] = None,
    custom_js: Optional[str] = None,
    css_file: str = "styles.css"
) -> str:
    """
    Generate HTML report with maximum security.

    Args:
        stats: Classification statistics
        table_rows: Pre-escaped HTML table rows
        is_truncated: Whether table truncated
        total_significant: Total significant variants
        html_max_variants: Max variants in HTML
        output_filename: Base filename
        custom_css: Optional custom CSS
        custom_js: Optional custom JS
        css_file: External CSS path

    Returns:
        Complete HTML document
    """
    stats = _validate_stats(stats)
    nonce = _generate_nonce()
    safe_css = _validate_css_path(css_file)
    safe_custom_css = _validate_custom_code(custom_css, 'CSS')
    safe_custom_js = _validate_custom_code(custom_js, 'JS')
    safe_fname = html.escape(output_filename)

    try:
        dt = datetime.now()
        current_time = dt.strftime('%Y-%m-%d %H:%M:%S')
        current_date = dt.strftime('%Y-%m-%d')
    except:
        current_time = current_date = "N/A"

    css_block = f'<style nonce="{nonce}">{safe_custom_css}</style>' if safe_custom_css else ""
    js_block = f'<script nonce="{nonce}">{safe_custom_js}</script>' if safe_custom_js else ""

    stats_dash = build_stats_dashboard(stats, nonce)
    legend = build_classification_legend(stats, nonce)
    warning = build_truncation_warning(is_truncated, html_max_variants, total_significant, safe_fname)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="Genetic variant analysis with ACMG classifications">
    <meta name="author" content="VariDex v{__version__}">
    <meta http-equiv="Content-Security-Policy" 
          content="default-src 'self'; style-src 'self' 'nonce-{nonce}'; script-src 'self' 'nonce-{nonce}'; img-src 'self' data: https:; connect-src 'none'; frame-ancestors 'none'; base-uri 'self'; form-action 'none';">
    <meta http-equiv="X-Content-Type-Options" content="nosniff">
    <meta http-equiv="X-Frame-Options" content="DENY">
    <meta name="referrer" content="no-referrer">
    <title>Genetic Analysis - {current_date}</title>
    <link rel="stylesheet" href="{safe_css}">
    {css_block}
</head>
<body>
    <div class="container" role="main">
        <header>
            <h1>🧬 Genetic Analysis Report</h1>
            <div class="subtitle">
                <strong>Generated:</strong> {current_time} | 
                <strong>Pipeline:</strong> VariDex v{__version__} |
                <strong>Total:</strong> {stats['total']:,}
            </div>
        </header>
        <div class="disclaimer" role="alert">
            <h3>⚠️ IMPORTANT MEDICAL DISCLAIMER</h3>
            <p>This report is for <strong>RESEARCH and EDUCATIONAL</strong> purposes only. 
               It is <strong>NOT a clinical diagnosis</strong>. All pathogenic findings 
               <strong>must be confirmed</strong> by a CLIA-certified laboratory.</p>
        </div>
        {warning}
        {stats_dash}
        {legend}
        <section aria-labelledby="variants-heading">
            <h2 id="variants-heading">Clinically Significant Variants</h2>
            <div class="filter-box" role="search">
                <label for="searchBox"><strong>🔍 Filter:</strong></label>
                <input type="text" id="searchBox" placeholder="Type to filter..." 
                       onkeyup="filterTable()" aria-label="Filter variants" maxlength="100">
            </div>
            <div class="table-container">
                <table id="variantTable">
                    <thead>
                        <tr>
                            <th scope="col">Icon</th><th scope="col">rsID</th><th scope="col">Gene</th>
                            <th scope="col">Genotype</th><th scope="col">Zygosity</th>
                            <th scope="col">Classification</th><th scope="col">Stars</th>
                            <th scope="col">Evidence</th>
                        </tr>
                    </thead>
                    <tbody>{table_rows}</tbody>
                </table>
            </div>
        </section>
        <footer class="footer" role="contentinfo">
            <p><strong>Data:</strong> ClinVar (NCBI/NLM) | <strong>Method:</strong> ACMG 2015</p>
            <p style="margin-top:20px; font-size:0.85em; color:#999;">VariDex v{__version__} | {current_time}</p>
        </footer>
    </div>
    <script nonce="{nonce}">
        function filterTable() {{
            try {{
                const input = document.getElementById('searchBox');
                if (!input) return;
                const filter = (input.value || '').replace(/[^a-zA-Z0-9 \\-_]/g, '').substring(0, 100).toUpperCase();
                const table = document.getElementById('variantTable');
                if (!table) return;
                const rows = table.getElementsByTagName('tr');
                for (let i = 1; i < rows.length; i++) {{
                    const text = rows[i].textContent || rows[i].innerText;
                    rows[i].style.display = text.toUpperCase().indexOf(filter) > -1 ? '' : 'none';
                }}
            }} catch (e) {{ console.error('Filter error:', e); }}
        }}
        document.addEventListener('keydown', function(e) {{
            if ((e.ctrlKey || e.metaKey) && e.key === 'f') {{
                e.preventDefault();
                const sb = document.getElementById('searchBox');
                if (sb) sb.focus();
            }}
        }});
        console.log('VariDex v{__version__} loaded with CSP nonce');
    </script>
    {js_block}
</body>
</html>"""


def generate_minimal_template(stats: Dict[str, int], table_rows: str = "") -> str:
    """Generate minimal fallback template."""
    stats = _validate_stats(stats)
    try:
        dt = datetime.now()
        current_time = dt.strftime('%Y-%m-%d %H:%M:%S')
        current_date = dt.strftime('%Y-%m-%d')
    except:
        current_time = current_date = "N/A"

    pc = stats['pathogenic'] + stats['likely_pathogenic']

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="X-Content-Type-Options" content="nosniff">
    <title>Genetic Report - {current_date}</title>
    <style>
        body {{font-family:Arial,sans-serif; margin:20px; background:#f5f5f5;}}
        .container {{max-width:1200px; margin:0 auto; background:white; padding:30px; 
                    border-radius:8px; box-shadow:0 2px 10px rgba(0,0,0,0.1);}}
        h1 {{color:#333; border-bottom:3px solid #4CAF50; padding-bottom:10px;}}
        table {{width:100%; border-collapse:collapse; margin:20px 0;}}
        th {{background:#4CAF50; color:white; padding:12px; text-align:left;}}
        td {{padding:10px; border-bottom:1px solid #ddd;}}
        tr:hover {{background:#f5f5f5;}}
    </style>
</head>
<body>
    <div class="container">
        <h1>🧬 Genetic Analysis (Minimal)</h1>
        <p><strong>Generated:</strong> {current_time}</p>
        <p><strong>Total:</strong> {stats['total']:,} | <strong>Pathogenic/Likely:</strong> {pc}</p>
        <table>
            <thead><tr><th>Icon</th><th>rsID</th><th>Gene</th><th>Classification</th></tr></thead>
            <tbody>{table_rows if table_rows else '<tr><td colspan="4">No data</td></tr>'}</tbody>
        </table>
    </div>
</body>
</html>"""


if __name__ == "__main__":
    print("=" * 70)
    print("HTML TEMPLATE BUILDER v6.0.0")
    print("=" * 70)
    test_stats = {
        'total': 1000, 'pathogenic': 5, 'likely_pathogenic': 3,
        'vus': 50, 'likely_benign': 200, 'benign': 742, 'conflicts': 2
    }
    try:
        html = generate_html_template(
            stats=test_stats,
            table_rows='<tr><td>🔴</td><td>rs123</td><td>BRCA1</td><td>A/G</td><td>Het</td><td>Pathogenic</td><td>⭐⭐⭐</td><td>PVS1</td></tr>',
            is_truncated=False,
            total_significant=58,
            html_max_variants=100,
            output_filename='test'
        )
        print(f"Generated: {len(html):,} chars")
        assert 'nonce-' in html and 'unsafe-inline' not in html
        print("Security: PASS ✅")
    except ImportError:
        print("NOTE: components.py not found - create it first")
    print("=" * 70)
