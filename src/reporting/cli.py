"""CLI interface for reporting module."""

import click
from .core import ReportGenerator, QCDashboard
from .models import AnnotatedVariant


def run_pipeline(input_vcf):  # Mock pipeline for testing
    """Mock pipeline returning sample variants."""
    return [
        AnnotatedVariant("1", 100, "A", "T", "P", 0.01),
        AnnotatedVariant("2", 200, "C", "G", "B", 0.05),
    ]


@click.group()
def reporting():
    """VariDex reporting commands."""
    pass


@reporting.command()
@click.argument("input_vcf")
@click.option("--html", "-H", help="HTML report path")
@click.option("--tsv", "-t", help="TSV export path")
@click.option("--json", "-j", help="JSON export path")
@click.option("--qc", "-q", help="QC metrics JSON")
def generate(
    input_vcf: str, html: str = None, tsv: str = None, json: str = None, qc: str = None
):
    """Generate reports from annotated VCF."""
    variants = run_pipeline(input_vcf)
    generator = ReportGenerator(variants)

    if html:
        generator.generate_html(html)
        click.echo(f"HTML report: {html}")
    if tsv:
        generator.generate_tsv(tsv)
        click.echo(f"TSV export: {tsv}")
    if json:
        generator.generate_json(json)
        click.echo(f"JSON export: {json}")
    if qc:
        dashboard = QCDashboard(variants)
        import json

        with open(qc, "w") as f:
            json.dump(dashboard.get_metrics(), f, indent=2)
        click.echo(f"QC metrics: {qc}")


if __name__ == "__main__":
    reporting()
