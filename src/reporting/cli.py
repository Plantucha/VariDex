"""CLI interface for reporting module."""
import click
from .core import ReportGenerator, QCDashboard
from src.pipeline.orchestrator import run_pipeline

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
def generate(input_vcf: str, html: str, tsv: str, json: str, qc: str):
    """Generate reports from annotated VCF."""
    variants = run_pipeline(input_vcf)  # Mock pipeline call
    generator = ReportGenerator(variants)
    
    if html:
        generator.generate_html(html)
    if tsv:
        generator.generate_tsv(tsv)
    if json:
        generator.generate_json(json)
    if qc:
        dashboard = QCDashboard(variants)
        import json
        with open(qc, "w") as f:
            json.dump(dashboard.get_metrics(), f, indent=2)

if __name__ == "__main__":
    reporting()
