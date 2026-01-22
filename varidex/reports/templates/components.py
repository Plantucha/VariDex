#!/usr/bin/env python3
"""
varidex/reports/templates/components.py - HTML Components v6.0.0

Reusable HTML component generators for variant reports.

Security: All user data is HTML-escaped, no inline JavaScript, CSP-compatible.
Components: Summary cards, variant table, classification legend, report footer.
"""

import html
from typing import Dict, Optional
from datetime import datetime

try:
    from varidex.version import __version__
except ImportError:
    __version__ = "6.0.0"

__all__ = [
    "generate_summary_cards",
    "generate_variant_table",
    "generate_legend",
    "generate_footer",
    "escape_table_row",
]


def generate_summary_cards(stats: Dict[str, int]) -> str:
    """Generate statistics summary cards HTML with ACMG classifications.

    Args:
        stats: Dict with keys: total, pathogenic, likely_pathogenic, vus,
               likely_benign, benign, conflicts
    Returns:
        HTML string for summary cards and classification grid
    """
    stats.get("total", 0)
    pathogenic = stats.get("pathogenic", 0)
    likely_pathogenic = stats.get("likely_pathogenic", 0)
    stats.get("vus", 0)
    stats.get("likely_benign", 0)
    stats.get("benign", 0)
    stats.get("conflicts", 0)
    pathogenic + likely_pathogenic

    return """
    <section aria-labelledby="stats-heading">
        <h2 id="stats-heading">Summary Statistics</h2>
        <div class="stats">
            <div class="stat-box"><h3>{total:,}</h3><p>Total Analyzed</p></div>
            <div class="stat-box"><h3>{pathogenic_combined}</h3><p>Pathogenic/Likely</p></div>
            <div class="stat-box"><h3>{vus}</h3><p>Uncertain (VUS)</p></div>
            <div class="stat-box"><h3>{conflicts}</h3><p>Conflicts</p></div>
        </div>
    </section>
    <section aria-labelledby="classification-heading">
        <h2 id="classification-heading">ACMG Classification Distribution</h2>
        <div class="classification-grid">
            <div class="class-box pathogenic"><h4>🔴 {pathogenic}</h4><p>Pathogenic</p></div>
            <div class="class-box likely-path"><h4>🟠 {likely_pathogenic}</h4><p>Likely Pathogenic</p></div>
            <div class="class-box vus"><h4>🟡 {vus}</h4><p>VUS</p></div>
            <div class="class-box likely-benign"><h4>🟢 {likely_benign}</h4><p>Likely Benign</p></div>
            <div class="class-box benign"><h4>✅ {benign}</h4><p>Benign</p></div>
        </div>
    </section>"""


def generate_variant_table(
    table_rows_html: str,
    is_truncated: bool = False,
    total_variants: int = 0,
    max_displayed: int = 1000,
) -> str:
    """Generate main variant results table HTML.

    Args:
        table_rows_html: Pre-generated <tr> HTML (MUST be pre-escaped)
        is_truncated: Whether table is truncated
        total_variants: Total variant count
        max_displayed: Maximum variants displayed
    Returns:
        HTML string for variant table with optional truncation warning
    """
    truncation_warning = ""
    if is_truncated:
        truncation_warning = """
        <div class="warning" role="alert" aria-live="polite">
            <strong>⚠️ TABLE TRUNCATED:</strong> Showing top {max_displayed:,} of
            <strong>{total_variants:,}</strong> clinically significant variants.
            <br><br>📄 See CSV file for complete dataset.
        </div>"""

    return """
    <section aria-labelledby="variants-heading">
        <h2 id="variants-heading">Clinically Significant Variants</h2>
        {truncation_warning}
        <div class="filter-box" role="search">
            <label for="searchBox"><strong>🔍 Filter Table:</strong></label>
            <input type="text" id="searchBox" placeholder="Type to filter..."
                   onkeyup="filterTable()" aria-label="Filter variants" maxlength="100">
        </div>
        <div class="table-container">
            <table id="variantTable">
                <thead>
                    <tr>
                        <th scope="col">Icon</th>
                        <th scope="col">rsID</th>
                        <th scope="col">Gene</th>
                        <th scope="col">Genotype</th>
                        <th scope="col">Zygosity</th>
                        <th scope="col">Classification</th>
                        <th scope="col">Stars</th>
                        <th scope="col">Evidence</th>
                    </tr>
                </thead>
                <tbody>{table_rows_html}</tbody>
            </table>
        </div>
    </section>"""


def generate_legend() -> str:
    """Generate ACMG classification legend HTML.

    Returns:
        HTML string with classification descriptions and ACMG 2015 reference
    """
    return """
    <section aria-labelledby="legend-heading">
        <h2 id="legend-heading">Classification Legend</h2>
        <div class="legend">
            <div class="legend-item legend-pathogenic">
                <span class="legend-icon">🔴</span>
                <span class="legend-name">Pathogenic</span>
                <span class="legend-desc">Strong evidence of disease causation</span>
            </div>
            <div class="legend-item legend-likely-pathogenic">
                <span class="legend-icon">🟠</span>
                <span class="legend-name">Likely Pathogenic</span>
                <span class="legend-desc">Moderate evidence of disease causation</span>
            </div>
            <div class="legend-item legend-vus">
                <span class="legend-icon">🟡</span>
                <span class="legend-name">Uncertain Significance (VUS)</span>
                <span class="legend-desc">Insufficient evidence to classify</span>
            </div>
            <div class="legend-item legend-likely-benign">
                <span class="legend-icon">🟢</span>
                <span class="legend-name">Likely Benign</span>
                <span class="legend-desc">Moderate evidence of no disease association</span>
            </div>
            <div class="legend-item legend-benign">
                <span class="legend-icon">✅</span>
                <span class="legend-name">Benign</span>
                <span class="legend-desc">Strong evidence of no disease association</span>
            </div>
            <div class="legend-reference">
                <strong>Reference:</strong> Richards et al. 2015, PMID 25741868
                (ACMG/AMP Standards and Guidelines)
            </div>
        </div>
    </section>"""


def generate_footer(
    timestamp: Optional[str] = None, total_variants: int = 0, output_filename: str = "report"
) -> str:
    """Generate report footer HTML with metadata and disclaimer.

    Args:
        timestamp: Report generation timestamp (auto-generated if None)
        total_variants: Total variant count
        output_filename: Base filename for download links (HTML-escaped)
    Returns:
        HTML footer with version info, disclaimer, and download links
    """
    if timestamp is None:
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            timestamp = "N/A"

    html.escape(output_filename)
    html.escape(timestamp)

    return """
    <footer class="footer" role="contentinfo">
        <div class="footer-content">
            <div class="footer-info">
                <p><strong>Generated:</strong> {safe_timestamp}</p>
                <p><strong>Total Variants:</strong> {total_variants:,}</p>
                <p><strong>VariDex Version:</strong> v{__version__}</p>
                <p><strong>Data Sources:</strong> ClinVar Database (NCBI/NLM)</p>
                <p><strong>Analysis Method:</strong> ACMG/AMP 2015 Guidelines</p>
            </div>
            <div class="footer-disclaimer">
                <h3>⚠️ IMPORTANT MEDICAL DISCLAIMER</h3>
                <p class="disclaimer">
                    This report is for <strong>RESEARCH and EDUCATIONAL</strong> purposes only.
                    It is <strong>NOT a clinical diagnosis</strong>. All pathogenic findings
                    <strong>must be confirmed</strong> by a CLIA-certified clinical laboratory
                    before any medical decisions are made.
                </p>
            </div>
            <div class="footer-downloads">
                <h3>Download Complete Results</h3>
                <ul>
                    <li><a href="{safe_filename}.csv">📄 CSV File</a></li>
                    <li><a href="{safe_filename}.json">📋 JSON File</a></li>
                </ul>
            </div>
        </div>
        <p style="margin-top: 20px; font-size: 0.85em; color: #999; text-align: center;">
            Generated by VariDex v{__version__} | {safe_timestamp}
        </p>
    </footer>"""


def escape_table_row(row_data: Dict) -> str:
    """Escape all fields in a table row for safe HTML rendering.

    Args:
        row_data: Dict with keys: icon, rsid, gene, genotype, zygosity,
                  classification, evidence, stars
    Returns:
        HTML <tr> element with escaped content
    Example:
        >>> row = {'rsid': 'rs123', 'gene': 'BRCA1', 'stars': 4, ...}
        >>> html = escape_table_row(row)
    """
    html.escape(str(row_data.get("icon", "")))
    html.escape(str(row_data.get("rsid", "")))
    html.escape(str(row_data.get("gene", "")))
    html.escape(str(row_data.get("genotype", "")))
    html.escape(str(row_data.get("zygosity", "")))
    html.escape(str(row_data.get("classification", "")))
    html.escape(str(row_data.get("evidence", "")))
    "⭐" * int(row_data.get("stars", 0))

    return """    <tr>
        <td>{icon}</td><td>{rsid}</td><td>{gene}</td><td>{genotype}</td>
        <td>{zygosity}</td><td>{classification}</td><td>{stars}</td><td>{evidence}</td>
    </tr>"""


# ==================== SELF-TEST ====================

if __name__ == "__main__":
    print("=" * 70)
    print("HTML COMPONENTS v6.0.0 - Self-Test")
    print("=" * 70)
    # Test data
    stats = {
        "total": 1000,
        "pathogenic": 5,
        "likely_pathogenic": 12,
        "vus": 50,
        "likely_benign": 200,
        "benign": 733,
        "conflicts": 3,
    }
    # Test 1: Summary cards
    cards = generate_summary_cards(stats)
    assert "1,000" in cards and "🔴" in cards
    print("✓ Test 1: Summary cards")
    # Test 2: Table with truncation
    table = generate_variant_table("<tr><td>Test</td></tr>", True, 5000, 1000)
    assert "Showing top 1,000" in table and "5,000" in table
    print("✓ Test 2: Variant table (truncated)")
    # Test 3: Table without truncation
    table_normal = generate_variant_table("<tr><td>Test</td></tr>")
    assert "TRUNCATED" not in table_normal
    print("✓ Test 3: Variant table (normal)")
    # Test 4: Legend
    legend = generate_legend()
    assert "Pathogenic" in legend and "PMID 25741868" in legend
    print("✓ Test 4: Classification legend")
    # Test 5: Footer (auto timestamp)
    footer = generate_footer(total_variants=1000, output_filename="report")
    assert __version__ in footer and "RESEARCH" in footer and "1,000" in footer
    print("✓ Test 5: Footer (auto timestamp)")
    # Test 6: Footer (custom timestamp)
    footer_custom = generate_footer("2026-01-19 15:30:00", 500, "custom")
    assert "2026-01-19 15:30:00" in footer_custom and "500" in footer_custom
    print("✓ Test 6: Footer (custom timestamp)")
    # Test 7: XSS protection (table row)
    evil_row = {
        "rsid": '<script>alert("XSS")</script>',
        "gene": "BRCA1<img src=x onerror=alert(1)>",
        "classification": "Pathogenic",
        "genotype": "A/G",
        "zygosity": "Het",
        "evidence": "PVS1",
        "stars": 4,
    }
    safe_row = escape_table_row(evil_row)
    assert "<script>" not in safe_row and "&lt;script&gt;" in safe_row
    assert "<img" not in safe_row
    print("✓ Test 7: XSS protection (table row)")
    # Test 8: XSS protection (footer)
    footer_evil = generate_footer(output_filename="<script>alert(1)</script>")
    assert "<script>" not in footer_evil
    print("✓ Test 8: XSS protection (footer)")
    print("=" * 70)
    print("All tests passed! Components ready for v{__version__}")
    print("=" * 70)
