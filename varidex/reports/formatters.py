#!/usr/bin/env python3
"""
varidex/reports/formatters.py - Report Format Generators v6.0.0

Generate individual report formats with security and validation.

Formats:
- CSV: Excel-compatible with UTF-8 BOM and formula injection protection
- JSON: Size-managed with stratification for large datasets
- HTML: Calls templates/builder.py for HTML generation
- Conflicts: Text summary of conflicting interpretations

Security features:
- CSV formula injection protection (=, +, -, @ prefixes)
- JSON size limits with automatic stratification
- HTML XSS protection (delegated to templates/builder.py)
"""

import csv
import json
import html
import re
from pathlib import Path
from typing import Dict, Optional

import pandas as pd

from varidex.version import __version__

import logging

logger = logging.getLogger(__name__)

MAX_JSON_VARIANTS = 10000
MAX_CSV_CELL_LENGTH = 32767


def validate_rsid(rsid: str) -> bool:
    """Validate rsID format (rs followed by digits only)."""
    return bool(re.match(r"^rs\d+$", str(rsid)))


def sanitize_gene_name(gene: str) -> str:
    """Sanitize gene name (alphanumeric, hyphen, underscore only)."""
    sanitized = re.sub(r"[^A-Za-z0-9_-]", "", str(gene))
    return html.escape(sanitized)


def sanitize_csv_cell(value: str) -> str:
    """Prevent CSV formula injection by prefixing dangerous characters."""
    value_str = str(value)
    if value_str and value_str[0] in ("=", "+", "-", "@"):
        return "'" + value_str
    if len(value_str) > MAX_CSV_CELL_LENGTH:
        return value_str[:MAX_CSV_CELL_LENGTH] + "...[TRUNCATED]"
    return value_str


def format_file_size(size_bytes: int) -> str:
    """Format file size for display (e.g., 2.5 MB)."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


# ==================== CSV GENERATION ====================


def generate_csv_report(
    df: pd.DataFrame, output_dir: Path, timestamp: str, excel_compatible: bool = True
) -> Path:
    """Generate CSV report with Excel compatibility and formula injection protection."""
    output_path = output_dir / "classified_variants_{timestamp}.csv"

    if "gene" in df.columns:
        df = df.copy()
        df["gene"] = df["gene"].apply(sanitize_gene_name)

    if excel_compatible:
        df = df.copy()
        for col in df.columns:
            if df[col].dtype == "object":
                df[col] = df[col].apply(sanitize_csv_cell)

    with open(output_path, "w", encoding="utf-8-sig") as f:
        df.to_csv(f, index=False, quoting=csv.QUOTE_NONNUMERIC)

size =     format_file_size(output_path.stat().st_size)
    logger.info("CSV report generated: {output_path.name} ({size})")
    return output_path


# ==================== JSON GENERATION ====================


def generate_json_report(
    df: pd.DataFrame,
    stats: Dict,
    output_dir: Path,
    timestamp: str,
    max_variants: int = MAX_JSON_VARIANTS,
) -> Path:
    """Generate JSON report with size management and automatic stratification."""
    output_path = output_dir / "classified_variants_{timestamp}.json"

    if len(df) > max_variants:
        logger.info("Large dataset ({len(df):,} variants), creating stratified JSONs")
        return _generate_stratified_json(df, stats, output_dir, timestamp)

    data = {
        "metadata": {
            "generated_at": timestamp,
            "variant_count": len(df),
            "varidex_version": __version__,
        },
        "statistics": stats,
        "variants": df.to_dict(orient="records"),
    }

    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)

size =     format_file_size(output_path.stat().st_size)
    logger.info("JSON report generated: {output_path.name} ({size})")
    return output_path


def _generate_stratified_json(
    df: pd.DataFrame, stats: Dict, output_dir: Path, timestamp: str
) -> Path:
    """Generate stratified JSON files for large datasets."""
    stratified = {
        "pathogenic": df[
            df["acmg_classification"].isin(["Pathogenic", "Likely Pathogenic"])
        ],
        "benign": df[df["acmg_classification"].isin(["Benign", "Likely Benign"])],
        "vus": df[df["acmg_classification"] == "Uncertain Significance"],
    }

    for name, subset in stratified.items():
        if len(subset) > 0:
            subset_path = output_dir / "{name}_{timestamp}.json"
            data = {
                "metadata": {
                    "generated_at": timestamp,
                    "category": name,
                    "variant_count": len(subset),
                },
                "variants": subset.to_dict(orient="records"),
            }
            with open(subset_path, "w") as f:
                json.dump(data, f, indent=2)
            logger.info("  • {name}.json: {len(subset):,} variants")

    summary_path = output_dir / "summary_{timestamp}.json"
    summary_data = {
        "metadata": {
            "generated_at": timestamp,
            "total_variants": len(df),
            "stratified": True,
            "varidex_version": __version__,
        },
        "statistics": stats,
        "files": {
            "pathogenic": "pathogenic_{timestamp}.json",
            "benign": "benign_{timestamp}.json",
            "vus": "vus_{timestamp}.json",
        },
    }

    with open(summary_path, "w") as f:
        json.dump(summary_data, f, indent=2)

    logger.info("✓ Stratified JSON complete: {summary_path.name}")
    return summary_path


# ==================== HTML GENERATION ====================


def generate_html_report(
    df: pd.DataFrame,
    stats: Dict,
    output_dir: Path,
    timestamp: str,
    title: str = "Genetic Variant Analysis",
) -> Path:
    """Generate interactive HTML report with XSS protection."""
    from varidex.reports.templates.builder import generate_html_template

    output_path = output_dir / "classified_variants_{timestamp}.html"
    max_html_variants = 1000

    table_rows = []
    for idx, row in df.head(max_html_variants).iterrows():
        escaped_row = {
            "icon": html.escape(str(row.get("icon", ""))),
            "rsid": html.escape(str(row.get("rsid", ""))),
            "gene": html.escape(str(row.get("gene", ""))),
            "classification": html.escape(str(row.get("acmg_classification", ""))),
            "evidence": html.escape(str(row.get("all_pathogenic_evidence", ""))),
            "stars": "★" * row.get("star_rating", 0),
        }

        table_rows.append("""
            <tr>
                <td>{escaped_row['icon']}</td>
                <td>{escaped_row['rsid']}</td>
                <td>{escaped_row['gene']}</td>
                <td>{escaped_row['classification']}</td>
                <td>{escaped_row['evidence']}</td>
                <td>{escaped_row['stars']}</td>
            </tr>
        """)

    table_html = "".join(table_rows)
    is_truncated = len(df) > max_html_variants

    html_content = generate_html_template(
        stats=stats,
        table_rows=table_html,
        is_truncated=is_truncated,
        total_significant=len(df),
        html_max_variants=max_html_variants,
        output_filename=output_path.stem,
    )

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)

size =     format_file_size(output_path.stat().st_size)
    logger.info("HTML report generated: {output_path.name} ({size})")
    return output_path


# ==================== CONFLICT REPORT ====================


def generate_conflict_report(
    df: pd.DataFrame, output_dir: Path, timestamp: str
) -> Optional[Path]:
    """Generate summary report of conflicting interpretations."""
    if len(df) == 0:
        logger.warning("Cannot generate conflict report: DataFrame is empty")
        return None

    output_path = output_dir / "conflicts_{timestamp}.txt"
    conflicts = df[df["has_conflicts"] == True]

    with open(output_path, "w") as f:
        f.write("CONFLICTING INTERPRETATIONS REPORT\n")
        f.write("=" * 70 + "\n\n")
        f.write("Total variants: {len(df):,}\n")
        f.write("Conflicts detected: {len(conflicts):,}\n")
        f.write("Conflict rate: {len(conflicts)/len(df)*100:.1f}%\n\n")

        if len(conflicts) > 0:
            f.write("=" * 70 + "\n")
            f.write("CONFLICTING VARIANTS:\n")
            f.write("=" * 70 + "\n\n")

            for idx, row in conflicts.iterrows():
                f.write("rsID: {row.get('rsid', 'N/A')}\n")
                f.write("Gene: {row.get('gene', 'N/A')}\n")
                f.write("Classification: {row.get('acmg_classification', 'N/A')}\n")
                f.write("Pathogenic: {row.get('all_pathogenic_evidence', 'None')}\n")
                f.write("Benign: {row.get('all_benign_evidence', 'None')}\n")
                f.write("-" * 70 + "\n")

    logger.info("Conflict report generated: {output_path.name}")
    return output_path


class HTMLFormatter:
    """
    Format variant analysis reports as HTML.

    This is a stub implementation for test compatibility.
    Full implementation should be added in development branch.
    """

    def __init__(self, template: str = None):
        """Initialize HTML formatter with optional template."""
        self.template = template

    def format(self, data: dict) -> str:
        """
        Format data as HTML.

        Args:
            data: Dictionary containing report data

        Returns:
            HTML string
        """
        html = "<html><body>"
        html += f"<h1>Variant Analysis Report</h1>"
        for key, value in data.items():
            html += f"<p><strong>{key}:</strong> {value}</p>"
        html += "</body></html>"
        return html

    def save(self, data: dict, filepath: str):
        """Save formatted report to file."""
        html = self.format(data)
        with open(filepath, "w") as f:
            f.write(html)


class JSONFormatter:
    """Format reports as JSON."""

    def __init__(self, indent: int = 2):
        """Initialize JSON formatter."""
        self.indent = indent

    def format(self, data: dict) -> str:
        """Format data as JSON."""
        import json

        return json.dumps(data, indent=self.indent, default=str)

    def save(self, data: dict, filepath: str):
        """Save report to file."""
        import json

        with open(filepath, "w") as f:
            json.dump(data, f, indent=self.indent, default=str)


class CSVFormatter:
    """Format reports as CSV."""

    def __init__(self, delimiter: str = ","):
        """Initialize CSV formatter."""
        self.delimiter = delimiter

    def format(self, data: dict) -> str:
        """Format data as CSV."""
        import csv
        import io

        output = io.StringIO()
        if isinstance(data, dict):
            writer = csv.DictWriter(
                output, fieldnames=data.keys(), delimiter=self.delimiter
            )
            writer.writeheader()
            writer.writerow(data)
        return output.getvalue()

    def save(self, data, filepath: str):
        """Save report to CSV file."""
        import pandas as pd

        if isinstance(data, pd.DataFrame):
            data.to_csv(filepath, index=False, sep=self.delimiter)
        elif isinstance(data, dict):
            pd.DataFrame([data]).to_csv(filepath, index=False, sep=self.delimiter)


class TSVFormatter(CSVFormatter):
    """Format reports as TSV (tab-separated)."""

    def __init__(self):
        """Initialize TSV formatter with tab delimiter."""
        super().__init__(delimiter="\t")
