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
from datetime import datetime

import pandas as pd

from varidex.version import __version__

import logging
logger = logging.getLogger(__name__)

MAX_JSON_VARIANTS = 10000
MAX_CSV_CELL_LENGTH = 32767

def validate_rsid(rsid: str) -> bool:
    """Validate rsID format (rs followed by digits only)."""
    return bool(re.match(r'^rs\d+$', str(rsid)))

def sanitize_gene_name(gene: str) -> str:
    """Sanitize gene name (alphanumeric, hyphen, underscore only)."""
    sanitized = re.sub(r'[^A-Za-z0-9_-]', '', str(gene))
    return html.escape(sanitized)

def sanitize_csv_cell(value: str) -> str:
    """Prevent CSV formula injection by prefixing dangerous characters."""
    value_str = str(value)
    if value_str and value_str[0] in ('=', '+', '-', '@'):
        return "'" + value_str
    if len(value_str) > MAX_CSV_CELL_LENGTH:
        return value_str[:MAX_CSV_CELL_LENGTH] + '...[TRUNCATED]'
    return value_str

def format_file_size(size_bytes: int) -> str:
    """Format file size for display (e.g., 2.5 MB)."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"

# ==================== CSV GENERATION ====================

def generate_csv_report(
    df: pd.DataFrame,
    output_dir: Path,
    timestamp: str,
    excel_compatible: bool = True
) -> Path:
    """Generate CSV report with Excel compatibility and formula injection protection."""
    output_path = output_dir / f"classified_variants_{timestamp}.csv"

    if 'gene' in df.columns:
        df = df.copy()
        df['gene'] = df['gene'].apply(sanitize_gene_name)

    if excel_compatible:
        df = df.copy()
        for col in df.columns:
            if df[col].dtype == 'object':
                df[col] = df[col].apply(sanitize_csv_cell)

    with open(output_path, 'w', encoding='utf-8-sig') as f:
        df.to_csv(f, index=False, quoting=csv.QUOTE_NONNUMERIC)

    size = format_file_size(output_path.stat().st_size)
    logger.info(f"CSV report generated: {output_path.name} ({size})")
    return output_path

# ==================== JSON GENERATION ====================

def generate_json_report(
    df: pd.DataFrame,
    stats: Dict,
    output_dir: Path,
    timestamp: str,
    max_variants: int = MAX_JSON_VARIANTS
) -> Path:
    """Generate JSON report with size management and automatic stratification."""
    output_path = output_dir / f"classified_variants_{timestamp}.json"

    if len(df) > max_variants:
        logger.info(f"Large dataset ({len(df):,} variants), creating stratified JSONs")
        return _generate_stratified_json(df, stats, output_dir, timestamp)

    data = {
        'metadata': {
            'generated_at': timestamp,
            'variant_count': len(df),
            'varidex_version': __version__,
        },
        'statistics': stats,
        'variants': df.to_dict(orient='records')
    }

    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2)

    size = format_file_size(output_path.stat().st_size)
    logger.info(f"JSON report generated: {output_path.name} ({size})")
    return output_path

def _generate_stratified_json(
    df: pd.DataFrame,
    stats: Dict,
    output_dir: Path,
    timestamp: str
) -> Path:
    """Generate stratified JSON files for large datasets."""
    stratified = {
        'pathogenic': df[df['acmg_classification'].isin(['Pathogenic', 'Likely Pathogenic'])],
        'benign': df[df['acmg_classification'].isin(['Benign', 'Likely Benign'])],
        'vus': df[df['acmg_classification'] == 'Uncertain Significance']
    }

    for name, subset in stratified.items():
        if len(subset) > 0:
            subset_path = output_dir / f"{name}_{timestamp}.json"
            data = {
                'metadata': {'generated_at': timestamp, 'category': name, 'variant_count': len(subset)},
                'variants': subset.to_dict(orient='records')
            }
            with open(subset_path, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"  • {name}.json: {len(subset):,} variants")

    summary_path = output_dir / f"summary_{timestamp}.json"
    summary_data = {
        'metadata': {
            'generated_at': timestamp,
            'total_variants': len(df),
            'stratified': True,
            'varidex_version': __version__
        },
        'statistics': stats,
        'files': {
            'pathogenic': f"pathogenic_{timestamp}.json",
            'benign': f"benign_{timestamp}.json",
            'vus': f"vus_{timestamp}.json"
        }
    }

    with open(summary_path, 'w') as f:
        json.dump(summary_data, f, indent=2)

    logger.info(f"✓ Stratified JSON complete: {summary_path.name}")
    return summary_path

# ==================== HTML GENERATION ====================

def generate_html_report(
    df: pd.DataFrame,
    stats: Dict,
    output_dir: Path,
    timestamp: str,
    title: str = "Genetic Variant Analysis"
) -> Path:
    """Generate interactive HTML report with XSS protection."""
    from varidex.reports.templates.builder import generate_html_template

    output_path = output_dir / f"classified_variants_{timestamp}.html"
    max_html_variants = 1000

    table_rows = []
    for idx, row in df.head(max_html_variants).iterrows():
        escaped_row = {
            'icon': html.escape(str(row.get('icon', ''))),
            'rsid': html.escape(str(row.get('rsid', ''))),
            'gene': html.escape(str(row.get('gene', ''))),
            'classification': html.escape(str(row.get('acmg_classification', ''))),
            'evidence': html.escape(str(row.get('all_pathogenic_evidence', ''))),
            'stars': '★' * row.get('star_rating', 0)
        }

        table_rows.append(f"""
            <tr>
                <td>{escaped_row['icon']}</td>
                <td>{escaped_row['rsid']}</td>
                <td>{escaped_row['gene']}</td>
                <td>{escaped_row['classification']}</td>
                <td>{escaped_row['evidence']}</td>
                <td>{escaped_row['stars']}</td>
            </tr>
        """)

    table_html = ''.join(table_rows)
    is_truncated = len(df) > max_html_variants

    html_content = generate_html_template(
        stats=stats,
        table_rows=table_html,
        is_truncated=is_truncated,
        total_significant=len(df),
        html_max_variants=max_html_variants,
        output_filename=output_path.stem
    )

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    size = format_file_size(output_path.stat().st_size)
    logger.info(f"HTML report generated: {output_path.name} ({size})")
    return output_path

# ==================== CONFLICT REPORT ====================

def generate_conflict_report(
    df: pd.DataFrame,
    output_dir: Path,
    timestamp: str
) -> Optional[Path]:
    """Generate summary report of conflicting interpretations."""
    if len(df) == 0:
        logger.warning("Cannot generate conflict report: DataFrame is empty")
        return None

    output_path = output_dir / f"conflicts_{timestamp}.txt"
    conflicts = df[df['has_conflicts'] == True]

    with open(output_path, 'w') as f:
        f.write("CONFLICTING INTERPRETATIONS REPORT\n")
        f.write("=" * 70 + "\n\n")
        f.write(f"Total variants: {len(df):,}\n")
        f.write(f"Conflicts detected: {len(conflicts):,}\n")
        f.write(f"Conflict rate: {len(conflicts)/len(df)*100:.1f}%\n\n")

        if len(conflicts) > 0:
            f.write("=" * 70 + "\n")
            f.write("CONFLICTING VARIANTS:\n")
            f.write("=" * 70 + "\n\n")

            for idx, row in conflicts.iterrows():
                f.write(f"rsID: {row.get('rsid', 'N/A')}\n")
                f.write(f"Gene: {row.get('gene', 'N/A')}\n")
                f.write(f"Classification: {row.get('acmg_classification', 'N/A')}\n")
                f.write(f"Pathogenic: {row.get('all_pathogenic_evidence', 'None')}\n")
                f.write(f"Benign: {row.get('all_benign_evidence', 'None')}\n")
                f.write("-" * 70 + "\n")

    logger.info(f"Conflict report generated: {output_path.name}")
    return output_path
