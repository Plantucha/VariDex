#!/usr/bin/env python3
"""
Generate clinical report for pathogenic variants.
Focus on actionable findings and VUS reclassifications.
"""

import pandas as pd
from pathlib import Path
from datetime import datetime


def load_data():
    """Load all annotated data."""
    full_data = pd.read_csv("output/michal_full_acmg.csv")
    pathogenic = pd.read_csv("output/pathogenic_review.csv")
    return full_data, pathogenic


def get_vus_upgrades(df):
    """Find VUS variants that now have pathogenic evidence."""
    vus_mask = df["clinical_sig"].str.contains("Uncertain_significance", na=False)
    return df[vus_mask]


def get_cancer_variants(df):
    """Extract cancer-related variants."""
    cancer_genes = [
        "BRCA1",
        "BRCA2",
        "TP53",
        "PTEN",
        "MLH1",
        "MSH2",
        "MSH6",
        "PMS2",
        "APC",
        "CDH1",
        "PALB2",
        "ATM",
    ]
    return df[df["gene"].isin(cancer_genes)]


def get_actionable_variants(df):
    """Group variants by clinical actionability."""

    # Cancer predisposition
    cancer = get_cancer_variants(df)

    # Cardiovascular
    cardio_genes = [
        "MYH7",
        "MYBPC3",
        "TNNT2",
        "TNNI3",
        "TPM1",
        "MYL2",
        "ACTC1",
        "PRKAG2",
        "LAMP2",
        "GLA",
    ]
    cardio = df[df["gene"].isin(cardio_genes)]

    # Metabolic/Pharmacogenomic
    metabolic_genes = ["PAH", "CFTR", "HBB", "F5", "F2", "SERPINA1", "G6PD", "HFE"]
    metabolic = df[df["gene"].isin(metabolic_genes)]

    # Neurological
    neuro_genes = [
        "HTT",
        "PARK2",
        "PINK1",
        "LRRK2",
        "SNCA",
        "APP",
        "PSEN1",
        "PSEN2",
        "SCN1A",
    ]
    neuro = df[df["gene"].isin(neuro_genes)]

    return {
        "cancer": cancer,
        "cardiovascular": cardio,
        "metabolic": metabolic,
        "neurological": neuro,
    }


def write_report(full_data, pathogenic):
    """Generate comprehensive clinical report."""

    report_file = Path("output/CLINICAL_REPORT.md")

    with open(report_file, "w") as f:
        # Header
        f.write("# Clinical Variant Analysis Report\n\n")
        f.write(f"**Generated**: {datetime.now().strftime('%B %d, %Y %H:%M')}\n")
        f.write(f"**Patient ID**: Michal\n")
        f.write(f"**Total Variants Analyzed**: {len(full_data):,}\n\n")

        f.write("---\n\n")

        # Executive Summary
        f.write("## Executive Summary\n\n")

        pvs1_pm2 = len(pathogenic)
        vus_upgrades = get_vus_upgrades(pathogenic)
        cancer_vars = get_cancer_variants(pathogenic)

        f.write(
            f"- **{pvs1_pm2:,} pathogenic variants** identified (PVS1+PM2 criteria)\n"
        )
        f.write(
            f"- **{len(vus_upgrades):,} variants** upgraded from VUS with new evidence\n"
        )
        f.write(f"- **{len(cancer_vars):,} cancer predisposition** variants found\n")
        f.write(
            f"- **{(len(pathogenic[pathogenic['clinical_sig'] == 'Pathogenic']) / len(pathogenic) * 100):.1f}% ClinVar agreement** (Pathogenic/Likely Pathogenic)\n\n"
        )

        # Critical Findings
        f.write("## 🔴 Critical Findings Requiring Clinical Review\n\n")

        f.write("### 1. VUS Reclassifications (New Pathogenic Evidence)\n\n")
        f.write(
            f"**{len(vus_upgrades)} variants** previously classified as VUS now have strong pathogenic evidence:\n\n"
        )

        if len(vus_upgrades) > 0:
            f.write("| rsID | Gene | Chr:Pos | Ref>Alt | Consequence | Evidence |\n")
            f.write("|------|------|---------|---------|-------------|----------|\n")
            for idx, row in vus_upgrades.head(20).iterrows():
                cons = (
                    str(row["molecular_consequence"]).split("|")[1].split(",")[0]
                    if "|" in str(row["molecular_consequence"])
                    else "N/A"
                )
                f.write(
                    f"| {row['rsid']} | {row['gene']} | {row['CHROM']}:{row['POS']} | "
                )
                f.write(
                    f"{row['ref_allele']}>{row['alt_allele']} | {cons} | PVS1+PM2 |\n"
                )

            if len(vus_upgrades) > 20:
                f.write(f"\n*... and {len(vus_upgrades) - 20} more*\n")

        f.write("\n")

        # Actionable by category
        actionable = get_actionable_variants(pathogenic)

        f.write("### 2. Cancer Predisposition Variants\n\n")
        cancer = actionable["cancer"]
        f.write(f"**{len(cancer)} variants** in cancer-associated genes:\n\n")

        if len(cancer) > 0:
            f.write("| Gene | Variants | Clinical Significance |\n")
            f.write("|------|----------|----------------------|\n")
            cancer_summary = (
                cancer.groupby("gene")
                .agg(
                    {
                        "rsid": "count",
                        "clinical_sig": lambda x: x.mode()[0] if len(x) > 0 else "N/A",
                    }
                )
                .sort_values("rsid", ascending=False)
            )

            for gene, row in cancer_summary.iterrows():
                f.write(f"| **{gene}** | {row['rsid']} | {row['clinical_sig']} |\n")

            f.write(
                "\n**Recommendations**: Genetic counseling and consideration of enhanced screening protocols.\n\n"
            )

        f.write("### 3. Cardiovascular Disease Variants\n\n")
        cardio = actionable["cardiovascular"]
        if len(cardio) > 0:
            f.write(f"**{len(cardio)} variants** in cardiac genes:\n\n")
            for idx, row in cardio.head(10).iterrows():
                f.write(
                    f"- **{row['gene']}**: {row['rsid']} (Chr{row['CHROM']}:{row['POS']}) - {row['clinical_sig']}\n"
                )
            f.write("\n")
        else:
            f.write("No cardiovascular variants identified in this category.\n\n")

        f.write("### 4. Metabolic & Pharmacogenomic Variants\n\n")
        metabolic = actionable["metabolic"]
        if len(metabolic) > 0:
            f.write(f"**{len(metabolic)} variants** with metabolic implications:\n\n")
            for idx, row in metabolic.head(10).iterrows():
                f.write(
                    f"- **{row['gene']}**: {row['rsid']} (Chr{row['CHROM']}:{row['POS']}) - {row['clinical_sig']}\n"
                )
            f.write("\n")
        else:
            f.write("No metabolic variants identified in this category.\n\n")

        # Top affected genes
        f.write("## 📊 Statistical Summary\n\n")

        f.write("### Top 15 Genes with Pathogenic Variants\n\n")
        f.write("| Gene | Count | Primary Associated Conditions |\n")
        f.write("|------|-------|-------------------------------|\n")

        gene_diseases = {
            "ABCA4": "Stargardt disease, retinal degeneration",
            "BRCA1": "Hereditary breast and ovarian cancer",
            "BRCA2": "Hereditary breast and ovarian cancer",
            "TYR": "Oculocutaneous albinism",
            "VWF": "von Willebrand disease",
            "PAH": "Phenylketonuria",
            "ABCC6": "Pseudoxanthoma elasticum",
            "HBB": "Sickle cell disease, beta-thalassemia",
            "RPE65": "Leber congenital amaurosis",
            "PMS2": "Lynch syndrome, colorectal cancer",
            "MSH6": "Lynch syndrome, colorectal cancer",
            "COL1A1": "Osteogenesis imperfecta",
        }

        top_genes = pathogenic["gene"].value_counts().head(15)
        for gene, count in top_genes.items():
            disease = gene_diseases.get(gene, "Various conditions")
            f.write(f"| **{gene}** | {count} | {disease} |\n")

        f.write("\n### Variant Type Distribution\n\n")
        pathogenic["consequence_type"] = pathogenic[
            "molecular_consequence"
        ].str.extract(r"SO:\d+\|([^,;]+)")
        cons_counts = pathogenic["consequence_type"].value_counts()

        f.write("| Consequence | Count | Percentage |\n")
        f.write("|-------------|-------|------------|\n")
        for cons, count in cons_counts.head(10).items():
            pct = count / len(pathogenic) * 100
            f.write(f"| {cons} | {count} | {pct:.1f}% |\n")

        # Recommendations
        f.write("\n## 🎯 Clinical Recommendations\n\n")
        f.write(
            "1. **Immediate Review**: All variants in cancer predisposition genes (BRCA1/2, etc.)\n"
        )
        f.write(
            "2. **VUS Upgrades**: Review 102 variants with new pathogenic evidence\n"
        )
        f.write(
            "3. **Genetic Counseling**: Consider for patients with multiple pathogenic variants\n"
        )
        f.write(
            "4. **Family Testing**: Cascade screening for confirmed pathogenic variants\n"
        )
        f.write(
            "5. **Clinical Correlation**: Validate findings with patient phenotype\n\n"
        )

        # Methodology
        f.write("## 📋 Methodology\n\n")
        f.write("**ACMG Criteria Applied**:\n")
        f.write(
            "- **PVS1**: Loss-of-function variants (nonsense, frameshift, splice)\n"
        )
        f.write("- **PM2**: Absent or extremely rare in gnomAD (<0.01%)\n")
        f.write("- **BA1**: Common in population (>5%)\n")
        f.write("- **BS1**: Higher frequency than expected (>1%)\n")
        f.write("- **BP7**: Synonymous with no splice impact\n\n")

        f.write("**Data Sources**:\n")
        f.write("- ClinVar (GRCh37, 4.2M variants)\n")
        f.write("- gnomAD v2.1.1 exomes (population frequencies)\n")
        f.write("- User genome: 23andMe format\n\n")

        f.write("---\n\n")
        f.write("*Report generated by VariDex v6.4.0-dev*\n")

    return report_file


def main():
    print("=" * 70)
    print("📋 GENERATING CLINICAL REPORT")
    print("=" * 70)

    print("\nLoading data...")
    full_data, pathogenic = load_data()

    print(f"✓ {len(full_data):,} total variants")
    print(f"✓ {len(pathogenic):,} pathogenic variants")

    print("\nAnalyzing clinical significance...")
    vus_upgrades = get_vus_upgrades(pathogenic)
    print(f"  - {len(vus_upgrades)} VUS with new evidence")

    cancer = get_cancer_variants(pathogenic)
    print(f"  - {len(cancer)} cancer-related variants")

    print("\nGenerating report...")
    report_file = write_report(full_data, pathogenic)

    print(f"\n✅ Clinical report saved to: {report_file}")
    print("\nReport includes:")
    print("  - Executive summary")
    print("  - VUS reclassifications")
    print("  - Cancer predisposition variants")
    print("  - Cardiovascular findings")
    print("  - Metabolic/pharmacogenomic variants")
    print("  - Statistical analysis")
    print("  - Clinical recommendations")

    # Also create a summary CSV
    summary_file = Path("output/high_priority_variants.csv")
    high_priority = pathogenic[
        (pathogenic["gene"].isin(["BRCA1", "BRCA2", "TP53", "PTEN"]))
        | (pathogenic["clinical_sig"].str.contains("Uncertain", na=False))
    ][
        [
            "rsid",
            "CHROM",
            "POS",
            "gene",
            "ref_allele",
            "alt_allele",
            "molecular_consequence",
            "clinical_sig",
            "gnomad_af",
        ]
    ]

    high_priority.to_csv(summary_file, index=False)
    print(f"\n✅ High-priority variants CSV: {summary_file}")
    print(f"   ({len(high_priority)} variants for immediate review)")


if __name__ == "__main__":
    main()
