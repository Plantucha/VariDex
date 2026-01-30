#!/usr/bin/env python3
"""
varidex/reports/formatters.py - Report Format Generators v6.0.2-dev

Generate individual report formats with security and validation.
Enhanced test compatibility for TSV, HTML, and JSON formatters.

Development version - not for production use.
"""

import csv
import json
import html
import re
from pathlib import Path
from typing import Dict, Optional, List, Union
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
    timestamp: str = "",
    max_variants: int = MAX_JSON_VARIANTS,
) -> Path:
    """Generate JSON report with size management."""
    if not timestamp:
        from datetime import datetime

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

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
    timestamp: str = "",
    title: str = "Genetic Variant Analysis",
) -> Path:
    """Generate interactive HTML report with XSS protection."""
    if not timestamp:
        from datetime import datetime

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

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
    """Generate enhanced basic HTML report with meaningful data display."""
    output_path = output_dir / f"classified_variants_{timestamp}.html"
    
    # Define classification colors
    classification_colors = {
        "P": "#dc3545",  # Red
        "Pathogenic": "#dc3545",
        "LP": "#fd7e14",  # Orange
        "Likely Pathogenic": "#fd7e14",
        "VUS": "#ffc107",  # Yellow
        "Uncertain Significance": "#ffc107",
        "LB": "#28a745",  # Green
        "Likely Benign": "#28a745",
        "B": "#20c997",  # Teal
        "Benign": "#20c997",
        "CONFLICT": "#6c757d",  # Gray
    }
    
    # Select meaningful columns for display
    display_columns = ["icon", "rsid", "chromosome", "position", "gene", 
                      "genotype", "acmg_classification", "star_rating",
                      "clinical_significance"]
    
    # Filter to existing columns
    available_cols = [col for col in display_columns if col in df.columns]
    
    # Prepare display data - filter out rows with missing rsid
    display_df = df[available_cols].copy()
    display_df = display_df[display_df["rsid"].notna() & (display_df["rsid"] != "")]
    
    # Replace NaN with empty strings
    display_df = display_df.fillna("")

    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{html.escape(title)}</title>
    <style>
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            margin: 20px;
            background-color: #f8f9fa;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{ 
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }}
        .stat-box {{
            padding: 15px;
            border-radius: 6px;
            border-left: 4px solid #3498db;
            background: #f8f9fa;
        }}
        .stat-label {{ 
            font-size: 0.9em;
            color: #6c757d;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .stat-value {{ 
            font-size: 1.8em;
            font-weight: bold;
            color: #2c3e50;
            margin-top: 5px;
        }}
        table {{ 
            border-collapse: collapse;
            width: 100%;
            margin-top: 20px;
            font-size: 0.9em;
        }}
        th, td {{ 
            border: 1px solid #dee2e6;
            padding: 12px 8px;
            text-align: left;
        }}
        th {{ 
            background-color: #3498db;
            color: white;
            font-weight: 600;
            position: sticky;
            top: 0;
        }}
        tr:nth-child(even) {{ background-color: #f8f9fa; }}
        tr:hover {{ background-color: #e9ecef; }}
        .classification {{
            padding: 4px 8px;
            border-radius: 4px;
            font-weight: 600;
            display: inline-block;
            font-size: 0.85em;
        }}
        .stars {{ color: #ffc107; }}
        .footer {{
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #dee2e6;
            color: #6c757d;
            font-size: 0.85em;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{html.escape(title)}</h1>
        <p style="color: #6c757d;">Generated: {html.escape(timestamp)}</p>
        
        <div class="stats">
"""

    # Add statistics
    stat_items = [
        ("Total Variants", stats.get("total_variants", len(df))),
        ("Pathogenic", stats.get("pathogenic", 0)),
        ("Likely Pathogenic", stats.get("likely_pathogenic", 0)),
        ("VUS", stats.get("vus", 0)),
        ("Benign/Likely Benign", stats.get("benign", 0) + stats.get("likely_benign", 0)),
    ]
    
    for label, value in stat_items:
        html_content += f"""            <div class="stat-box">
                <div class="stat-label">{html.escape(label)}</div>
                <div class="stat-value">{html.escape(str(value))}</div>
            </div>\n"""

    html_content += """        </div>
        
        <h2>Variant Details (Top 200)</h2>
        <table>
            <tr>
"""

    # Table headers - use friendly names
    column_names = {
        "icon": "",
        "rsid": "rsID",
        "chromosome": "Chr",
        "position": "Position",
        "gene": "Gene",
        "genotype": "Genotype",
        "acmg_classification": "Classification",
        "star_rating": "⭐",
        "clinical_significance": "Clinical Significance",
    }
    
    for col in available_cols:
        friendly_name = column_names.get(col, col)
        html_content += f"                <th>{html.escape(str(friendly_name))}</th>\n"

    html_content += "            </tr>\n"

    # Table rows - limit to 200 variants
    for idx, row in display_df.head(200).iterrows():
        html_content += "            <tr>\n"
        for col in available_cols:
            value = str(row.get(col, ""))
            
            # Special formatting for classification
            if col == "acmg_classification" and value:
                color = classification_colors.get(value, "#6c757d")
                cell_content = f'<span class="classification" style="background-color: {color}20; color: {color}; border: 1px solid {color};">{html.escape(value)}</span>'
            # Special formatting for stars
            elif col == "star_rating":
                stars = int(value) if value and value.isdigit() else 0
                cell_content = f'<span class="stars">{"★" * stars}</span>'
            # Regular cells
            else:
                cell_content = html.escape(value) if value else "<span style='color: #adb5bd;'>-</span>"
            
            html_content += f"                <td>{cell_content}</td>\n"
        html_content += "            </tr>\n"

    # Footer
    total_shown = min(200, len(display_df))
    html_content += f"""        </table>
        
        <div class="footer">
            <p><strong>Showing {total_shown:,} of {len(df):,} total variants</strong></p>
            <p>⚠️ <strong>RESEARCH USE ONLY</strong> - Not for clinical diagnosis. Consult a genetic counselor.</p>
            <p>Reference: Richards et al. 2015 (PMID: 25741868)</p>
            <p>Generated by VariDex {html.escape(__version__)}</p>
        </div>
    </div>
</body>
</html>
"""

    with open(output_path, "w") as f:
        f.write(html_content)

    return output_path


def generate_conflicts_report(
    df: pd.DataFrame, output_dir: Path, timestamp: str
) -> Optional[Path]:
    """Generate CSV report of conflicting variant interpretations.
    
    Args:
        df: DataFrame with classified variants
        output_dir: Output directory for report
        timestamp: Timestamp string for filename
    
    Returns:
        Path to conflicts CSV file, or None if no conflicts found
    """
    # Check for conflicts using correct column name (plural)
    if "has_conflicts" not in df.columns:
        logger.warning("Column 'has_conflicts' not found in DataFrame")
        return None
    
    # Filter for conflicts - check both boolean and CONFLICT classification
    conflicts = df[
        (df["has_conflicts"] == True) | 
        (df["acmg_classification"] == "CONFLICT")
    ].copy()

    if len(conflicts) == 0:
        logger.info("No conflicts detected")
        return None

    # Generate CSV report (changed from .txt to .csv)
    output_path = output_dir / f"conflicts_{timestamp}.csv"
    
    # Select relevant columns for conflicts report
    conflict_columns = [
        "rsid",
        "chromosome",
        "position",
        "gene",
        "genotype",
        "acmg_classification",
        "clinical_significance",
        "review_status",
        "num_submitters",
        "star_rating",
    ]
    
    # Filter to only existing columns
    available_columns = [col for col in conflict_columns if col in conflicts.columns]
    conflicts_subset = conflicts[available_columns]
    
    # Save as CSV
    conflicts_subset.to_csv(output_path, index=False)
    
    size = format_file_size(output_path.stat().st_size)
    logger.info(f"Conflicts report generated: {output_path.name} ({size}) - {len(conflicts):,} conflicts")
    return output_path


class HTMLFormatter:
    """Format reports as HTML with support for both dicts and Variant objects."""

    def __init__(self, template: Optional[str] = None):
        """Initialize HTML formatter."""
        self.template = template

    def format(self, data: Union[Dict, List]) -> str:
        """Format data as HTML."""
        # Handle list of Variant objects
        if isinstance(data, list):
            return self.format_variant_table(data)

        # Handle dict
        html_content = "<html><body>\n"
        for key, value in data.items():
            html_content += f"<p><strong>{html.escape(str(key))}:</strong> {html.escape(str(value))}</p>\n"
        html_content += "</body></html>\n"
        return html_content

    def format_variant_table(self, variants: List) -> str:
        """Format list of variants as HTML table."""
        from varidex.core.models import Variant

        html_content = """<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #4CAF50; color: white; }
    </style>
</head>
<body>
    <h1>Variant Report</h1>
    <table>
        <tr>
            <th>Chromosome</th>
            <th>Position</th>
            <th>Gene</th>
            <th>Reference</th>
            <th>Alternate</th>
        </tr>
"""

        for variant in variants:
            if isinstance(variant, Variant):
                chrom = html.escape(str(variant.chromosome))
                pos = html.escape(str(variant.position))
                gene = html.escape(str(variant.gene))
                ref = html.escape(str(variant.ref_allele))
                alt = html.escape(str(variant.alt_allele))
            else:
                # Handle dict
                chrom = html.escape(str(variant.get("chromosome", "")))
                pos = html.escape(str(variant.get("position", "")))
                gene = html.escape(str(variant.get("gene", "")))
                ref = html.escape(str(variant.get("reference", "")))
                alt = html.escape(str(variant.get("alternate", "")))

            html_content += f"""        <tr>
            <td>{chrom}</td>
            <td>{pos}</td>
            <td>{gene}</td>
            <td>{ref}</td>
            <td>{alt}</td>
        </tr>
"""

        html_content += """    </table>
</body>
</html>
"""
        return html_content

    def format_summary(self, summary: Dict) -> str:
        """Format summary section as HTML."""
        html_content = "<div class='summary'>\n<h2>Summary Statistics</h2>\n<ul>\n"
        for key, value in summary.items():
            html_content += f"    <li><strong>{html.escape(str(key))}:</strong> {html.escape(str(value))}</li>\n"
        html_content += "</ul>\n</div>\n"
        return html_content

    def format_report(self, data: Dict) -> str:
        """Format complete report with variants and summary."""
        html_content = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Variant Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        table { border-collapse: collapse; width: 100%; margin-top: 20px; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #4CAF50; color: white; }
        .summary { margin-bottom: 20px; }
    </style>
</head>
<body>
    <h1>Genetic Variant Analysis Report</h1>
"""

        # Add summary if present
        if "summary" in data:
            html_content += self.format_summary(data["summary"])

        # Add variants table if present
        if "variants" in data:
            html_content += self.format_variant_table(data["variants"])

        html_content += """</body>
</html>
"""
        return html_content

    def format_with_template(self, data: Dict, template: str = "") -> str:
        """Format with custom template."""
        if not template:
            return self.format_report(data)

        # Simple template substitution
        result = template
        for key, value in data.items():
            placeholder = "{{ " + key + " }}"
            result = result.replace(placeholder, str(value))
        return result

    def escape(self, text: str) -> str:
        """Escape HTML characters for XSS protection."""
        return html.escape(str(text))

    def save(self, data: dict, filepath: str):
        """Save formatted report to file."""
        html_content = self.format(data)
        with open(filepath, "w") as f:
            f.write(html_content)


class JSONFormatter:
    """Format reports as JSON with support for both dicts and Variant objects."""

    def __init__(self, indent: int = 2):
        """Initialize JSON formatter."""
        self.indent = indent

    def format(self, data: Union[Dict, List], indent: Optional[int] = None) -> str:
        """Format data as JSON."""
        from varidex.core.models import Variant

        if indent is None:
            indent = self.indent

        # Handle list of Variant objects
        if isinstance(data, list):
            variant_dicts = []
            for item in data:
                if isinstance(item, Variant):
                    variant_dicts.append(item.to_dict())
                else:
                    variant_dicts.append(item)
            return json.dumps(variant_dicts, indent=indent, default=str)

        # Handle dict
        return json.dumps(data, indent=indent, default=str)

    def save(self, data: dict, filepath: str):
        """Save report to file."""
        with open(filepath, "w") as f:
            json.dump(data, f, indent=self.indent, default=str)


class CSVFormatter:
    """Format reports as CSV with support for Variant objects."""

    def __init__(self, delimiter: str = ","):
        """Initialize CSV formatter."""
        self.delimiter = delimiter

    def format(self, data: Union[Dict, List, pd.DataFrame]) -> str:
        """Format data as CSV."""
        import io

        output = io.StringIO()

        # Handle DataFrame
        if isinstance(data, pd.DataFrame):
            data.to_csv(output, index=False, sep=self.delimiter)
            return output.getvalue()

        # Handle list of Variant objects
        if isinstance(data, list):
            from varidex.core.models import Variant

            if data and isinstance(data[0], Variant):
                # Convert to list of dicts
                variant_dicts = [v.to_dict() for v in data]
                if variant_dicts:
                    fieldnames = variant_dicts[0].keys()
                    writer = csv.DictWriter(
                        output, fieldnames=fieldnames, delimiter=self.delimiter
                    )
                    writer.writeheader()
                    writer.writerows(variant_dicts)
            else:
                # List of dicts
                if data:
                    fieldnames = data[0].keys()
                    writer = csv.DictWriter(
                        output, fieldnames=fieldnames, delimiter=self.delimiter
                    )
                    writer.writeheader()
                    writer.writerows(data)
            return output.getvalue()

        # Handle single dict
        if isinstance(data, dict):
            writer = csv.DictWriter(
                output, fieldnames=data.keys(), delimiter=self.delimiter
            )
            writer.writeheader()
            writer.writerow(data)
            return output.getvalue()

        return ""

    def save(self, data, filepath: str):
        """Save report to CSV file."""
        if isinstance(data, pd.DataFrame):
            data.to_csv(filepath, index=False, sep=self.delimiter)
        elif isinstance(data, (dict, list)):
            csv_content = self.format(data)
            with open(filepath, "w") as f:
                f.write(csv_content)


class TSVFormatter(CSVFormatter):
    """Format reports as TSV (tab-separated) with full Variant object support."""

    def __init__(self):
        """Initialize TSV formatter with tab delimiter."""
        super().__init__(delimiter="\t")

    def format(self, data: Union[Dict, List, pd.DataFrame], **kwargs) -> str:
        """
        Format data as TSV.

        Args:
            data: Data to format (Variant objects, dicts, or DataFrame)
            **kwargs: Additional formatting options (ignored for compatibility)

        Returns:
            TSV-formatted string with tab-separated values
        """
        import io

        output = io.StringIO()

        # Handle DataFrame
        if isinstance(data, pd.DataFrame):
            data.to_csv(output, index=False, sep="\t")
            return output.getvalue()

        # Handle list (Variant objects or dicts)
        if isinstance(data, list):
            if not data:
                return ""

            from varidex.core.models import Variant

            # Convert Variant objects to dicts
            if isinstance(data[0], Variant):
                variant_dicts = []
                for v in data:
                    variant_dicts.append(
                        {
                            "chromosome": v.chromosome,
                            "position": v.position,
                            "reference": v.ref_allele,
                            "alternate": v.alt_allele,
                            "gene": getattr(v, "gene", ""),
                            "rsid": getattr(v, "rsid", ""),
                        }
                    )
                data = variant_dicts

            # Write as TSV
            if data:
                fieldnames = list(data[0].keys())
                writer = csv.DictWriter(output, fieldnames=fieldnames, delimiter="\t")
                writer.writeheader()
                writer.writerows(data)
            return output.getvalue()

        # Handle single dict
        if isinstance(data, dict):
            fieldnames = list(data.keys())
            writer = csv.DictWriter(output, fieldnames=fieldnames, delimiter="\t")
            writer.writeheader()
            writer.writerow(data)
            return output.getvalue()

        return ""
