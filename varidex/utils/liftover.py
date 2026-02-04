#!/usr/bin/env python3
"""
VariDex Genomic Coordinate Liftover Utility (Development)
Converts 23andMe raw data between genome assemblies (GRCh37 <-> GRCh38)
Uses pyliftover for coordinate conversion with automatic chain file download
"""

import argparse
import sys
from pathlib import Path

import pandas as pd
from pyliftover import LiftOver


def liftover_23andme(
    input_file: Path,
    output_file: Path,
    source_build: str = "GRCh37",
    target_build: str = "GRCh38",
    skip_rows: int = 23,
) -> tuple[int, int, int]:
    """
    Liftover 23andMe raw data coordinates between genome builds.

    Args:
        input_file: Path to input 23andMe raw data file
        output_file: Path for output lifted file
        source_build: Source genome build (GRCh37 or GRCh38)
        target_build: Target genome build (GRCh37 or GRCh38)
        skip_rows: Number of header rows to skip

    Returns:
        Tuple of (total_variants, successful_lifts, failed_lifts)
    """
    print(f"\n🧬 VariDex Liftover: {source_build} → {target_build}")
    print(f"📂 Input: {input_file}")

    if source_build == target_build:
        raise ValueError(f"Source and target builds are the same: {source_build}")

    chain_map = {
        ("GRCh37", "GRCh38"): ("hg19", "hg38"),
        ("GRCh38", "GRCh37"): ("hg38", "hg19"),
    }

    chain_key = (source_build, target_build)
    if chain_key not in chain_map:
        raise ValueError(f"Unsupported conversion: {source_build} → {target_build}")

    source_chain, target_chain = chain_map[chain_key]
    print(f"⛓️  Chain: {source_chain}To{target_chain.capitalize()}")

    print(f"📥 Initializing LiftOver (may download chain files on first run)...")
    try:
        lo = LiftOver(source_chain, target_chain)
    except Exception as e:
        print(f"❌ Failed to initialize LiftOver: {e}")
        print("💡 Tip: Check internet connection for chain file download")
        sys.exit(1)

    print(f"📖 Reading input file...")
    try:
        df = pd.read_csv(
            input_file,
            sep="\t",
            comment="#",
            skiprows=skip_rows,
            names=["rsid", "chromosome", "position", "genotype"],
            dtype={"chromosome": str, "position": "Int64"},
            na_values=["--"],
            low_memory=False,
            on_bad_lines="skip",
        )
    except Exception as e:
        print(f"❌ Failed to read input file: {e}")
        sys.exit(1)

    total = len(df)
    print(f"✅ Loaded {total:,} variants")

    df_clean = df.dropna(subset=["chromosome", "position"]).copy()
    valid_chroms = [str(i) for i in range(1, 23)] + ["X", "Y", "MT"]
    df_clean = df_clean[df_clean["chromosome"].isin(valid_chroms)]

    print(f"🔄 Lifting over {len(df_clean):,} valid coordinates...")

    new_positions = []
    failed_count = 0
    progress_interval = max(1, len(df_clean) // 10)

    for idx, (_, row) in enumerate(df_clean.iterrows()):
        if idx > 0 and idx % progress_interval == 0:
            pct = (idx / len(df_clean)) * 100
            print(f"   Progress: {pct:.0f}% ({idx:,}/{len(df_clean):,})")

        chrom = f"chr{row['chromosome']}"
        pos = int(row["position"])

        result = lo.convert_coordinate(chrom, pos)

        if result and len(result) > 0:
            new_chrom, new_pos, *_ = result[0]
            new_positions.append(new_pos)
        else:
            new_positions.append(None)
            failed_count += 1

    df_clean["new_position"] = new_positions
    df_lifted = df_clean.dropna(subset=["new_position"]).copy()
    df_lifted["position"] = df_lifted["new_position"].astype("Int64")
    df_lifted = df_lifted[["rsid", "chromosome", "position", "genotype"]]

    output_file.parent.mkdir(parents=True, exist_ok=True)

    df_lifted.to_csv(output_file, sep="\t", index=False, header=False)

    success_count = len(df_lifted)

    print(f"\n📊 Liftover Summary:")
    print(f"   Total variants:     {total:,}")
    print(f"   Valid for liftover: {len(df_clean):,}")
    print(f"   Successful lifts:   {success_count:,} ({success_count/total*100:.1f}%)")
    print(f"   Failed lifts:       {failed_count:,} ({failed_count/total*100:.1f}%)")
    print(f"\n💾 Output saved: {output_file}")

    return total, success_count, failed_count


def main():
    parser = argparse.ArgumentParser(
        description="VariDex Liftover: Convert 23andMe coordinates between genome builds",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Convert GRCh37 to GRCh38 (default)
  python liftover.py rawM.txt --target GRCh38
  
  # Convert GRCh38 back to GRCh37
  python liftover.py rawM_lifted.txt --source GRCh38 --target GRCh37
  
  # Specify custom output directory
  python liftover.py rawM.txt --output-dir ./my_output
        """,
    )
    parser.add_argument("input_file", type=Path, help="Input 23andMe raw data file")
    parser.add_argument(
        "--target",
        choices=["GRCh37", "GRCh38"],
        default="GRCh38",
        help="Target genome build (default: GRCh38)",
    )
    parser.add_argument(
        "--source",
        choices=["GRCh37", "GRCh38"],
        default="GRCh37",
        help="Source genome build (default: GRCh37)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("liftover_output"),
        help="Output directory (default: liftover_output)",
    )
    parser.add_argument(
        "--skip-rows",
        type=int,
        default=23,
        help="Number of header rows to skip (default: 23)",
    )

    args = parser.parse_args()

    if not args.input_file.exists():
        print(f"❌ Input file not found: {args.input_file}")
        sys.exit(1)

    base_name = args.input_file.stem
    extension = args.input_file.suffix if args.input_file.suffix else ".txt"
    output_file = args.output_dir / f"{base_name}_liftover_{args.target}{extension}"

    try:
        liftover_23andme(
            args.input_file,
            output_file,
            source_build=args.source,
            target_build=args.target,
            skip_rows=args.skip_rows,
        )
        print("\n✅ Liftover completed successfully!")
    except Exception as e:
        print(f"\n❌ Liftover failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
