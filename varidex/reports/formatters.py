#!/usr/bin/env python3
"""
varidex/reports/formatters.py - Report Format Generators v6.0.1-dev

Generate individual report formats with security and validation.

Development version - not for production use.
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


def generate_csv_report(
    df: pd.DataFrame, output_dir: Path, timestamp: str, excel_compatible: bool = True
) -> Path:
    """Generate CSV report with Excel compatibility."""
    output_path = output_dir / f"classified_variants_{timestamp}.csv"

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

    size = format_file_size(output_path.stat().st_size)
    logger.info(f"CSV report generated: {output_path.name} ({size})")
    return output_path


def generate_json_report(
    df: pd.DataFrame,
    stats: Dict,
    output_dir: Path,
    timestamp: str,
    max_variants: int = MAX_JSON_VARIANTS,
) -> Path:
    """Generate JSON report with size management."""
    output_path = output_dir / f"classified_variants_{timestamp}.json"

    if len(df) > max_variants:
        logger.info(f"Large dataset ({len(df):,} variants), creating stratified JSONs")
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

    size = format_file_size(output_path.stat().st_size)
    logger.info(f"JSON report generated: {output_path.name} ({size})")
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
            subset_path = output_dir / f"{name}_{timestamp}.json"
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
            logger.info(f" • {name}.json: {len(subset):,} variants")

    summary_path = output_dir / f"summary_{timestamp}.json"
    summary_data = {
        "metadata": {
            "generated_at": timestamp,
            "total_variants": len(df),
            "stratified": True,
            "varidex_version": __version__,
        },
        "statistics": stats,
        "files": {
            "pathogenic": f"pathogenic_{timestamp}.json",
            "benign": f"benign_{timestamp}.json",
            "vus": f"vus_{timestamp}.json",
        },
    }

    with open(summary_path, "w") as f:
        json.dump(summary_data, f, indent=2)

    logger.info(f"✓ Stratified JSON complete: {summary_path.name}")
    return summary_path


def generate_html_report(
    df: pd.DataFrame,
    stats: Dict,
    output_dir: Path,
    timestamp: str,
    title: str = "Genetic Variant Analysis",
) -> Path:
    """Generate interactive HTML report with XSS protection."""
    try:
        from varidex.reports.templates.builder import generate_html_template
    except ImportError:
        logger.warning("HTML template builder not available, using basic HTML")
        return _generate_basic_html(df, stats, output_dir, timestamp, title)

    output_path = output_dir / f"classified_variants_{timestamp}.html"
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
        table_rows.append(escaped_row)

    html_content = generate_html_template(
        title=title, stats=stats, variants=table_rows, timestamp=timestamp
    )

    with open(output_path, "w") as f:
        f.write(html_content)

    size = format_file_size(output_path.stat().st_size)
    logger.info(f"HTML report generated: {output_path.name} ({size})")
    return output_path


def _generate_basic_html(
    df: pd.DataFrame, stats: Dict, output_dir: Path, timestamp: str, title: str
) -> Path:
    """Generate basic HTML report when template builder unavailable."""
    output_path = output_dir / f"classified_variants_{timestamp}.html"

    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{html.escape(title)}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #4CAF50; color: white; }}
    </style>
</head>
<body>
    <h1>{html.escape(title)}</h1>
    <p>Generated: {html.escape(timestamp)}</p>
    <h2>Statistics</h2>
    <ul>
"""

    for key, value in stats.items():
        html_content += f"        <li><strong>{html.escape(str(key))}:</strong> {html.escape(str(value))}</li>\n"

    html_content += """    </ul>
    <h2>Variants (first 100)</h2>
    <table>
        <tr>
"""

    for col in df.columns[:10]:
        html_content += f"            <th>{html.escape(str(col))}</th>\n"

    html_content += "        </tr>\n"

    for idx, row in df.head(100).iterrows():
        html_content += "        <tr>\n"
        for col in df.columns[:10]:
            value = html.escape(str(row.get(col, "")))
            html_content += f"            <td>{value}</td>\n"
        html_content += "        </tr>\n"

    html_content += """    </table>
</body>
</html>
"""

    with open(output_path, "w") as f:
        f.write(html_content)

    return output_path


def generate_conflicts_report(
    df: pd.DataFrame, output_dir: Path, timestamp: str
) -> Optional[Path]:
    """Generate text report of conflicting variant interpretations."""
    conflicts = df[df.get("has_conflict", False) == True]

    if len(conflicts) == 0:
        logger.info("No conflicts detected")
        return None

    output_path = output_dir / f"conflicts_{timestamp}.txt"

    with open(output_path, "w") as f:
        f.write(f"VARIANT INTERPRETATION CONFLICTS\n")
        f.write(f"Generated: {timestamp}\n")
        f.write(f"Total conflicts: {len(conflicts)}\n")
        f.write("=" * 70 + "\n\n")

        for idx, row in conflicts.iterrows():
            f.write(f"Variant: {row.get('rsid', 'Unknown')}\n")
            f.write(f"Gene: {row.get('gene', 'Unknown')}\n")
            f.write(f"Classification: {row.get('acmg_classification', 'Unknown')}\n")
            f.write(f"Conflicting interpretations: {row.get('conflict_count', 0)}\n")
            f.write("-" * 70 + "\n\n")

    logger.info(f"Conflicts report generated: {output_path.name}")
    return output_path


class HTMLFormatter:
    """Format reports as HTML."""

    def __init__(self, template: Optional[str] = None):
        """Initialize HTML formatter."""
        self.template = template

    def format(self, data: dict) -> str:
        """Format data as HTML."""
        html = "<html><body>\n"
        for key, value in data.items():
            html += f"<p><strong>{html.escape(str(key))}:</strong> {html.escape(str(value))}</p>\n"
        html += "</body></html>\n"
        return html

    def save(self, data: dict, filepath: str):
        """Save formatted report to file."""
        html_content = self.format(data)
        with open(filepath, "w") as f:
            f.write(html_content)


class JSONFormatter:
    """Format reports as JSON."""

    def __init__(self, indent: int = 2):
        """Initialize JSON formatter."""
        self.indent = indent

    def format(self, data: dict) -> str:
        """Format data as JSON."""
        return json.dumps(data, indent=self.indent, default=str)

    def save(self, data: dict, filepath: str):
        """Save report to file."""
        with open(filepath, "w") as f:
            json.dump(data, f, indent=self.indent, default=str)


class CSVFormatter:
    """Format reports as CSV."""

    def __init__(self, delimiter: str = ","):
        """Initialize CSV formatter."""
        self.delimiter = delimiter

    def format(self, data: dict) -> str:
        """Format data as CSV."""
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
        if isinstance(data, pd.DataFrame):
            data.to_csv(filepath, index=False, sep=self.delimiter)
        elif isinstance(data, dict):
            pd.DataFrame([data]).to_csv(filepath, index=False, sep=self.delimiter)


class TSVFormatter(CSVFormatter):
    """Format reports as TSV (tab-separated)."""

    def __init__(self):
        """Initialize TSV formatter with tab delimiter."""
        super().__init__(delimiter="\t")
