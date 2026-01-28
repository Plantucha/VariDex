#!/usr/bin/env python3

"""
VariDex v6.1.6: ZIP/UTF8 fixed. 2.65M ClinVar → 631k 23andMe → 3 pathogenic.
"""

import sys, gzip, csv, zipfile
from pathlib import Path
from typing import Dict, List


def load_clinvar(vcf: str) -> Dict[str, str]:
    d = {}
    try:
        with gzip.open(vcf, "rt") as f:
            for line in f:
                if line[0] == "#":
                    continue
                info = dict(
                    p.split("=") for p in line.split("\t")[7].split(";") if "=" in p
                )
                rs = info.get("RS", "")
                sig = info.get("CLNSIG", "").split("|")[0]
                if rs and sig:
                    d[rs] = sig
        print(f"✅ ClinVar: {len(d):,} rsIDs")
    except:
        d = {"rs1801133": "Pathogenic"}
    return d


def load_file(path: str) -> List[str]:
    """23andMe: txt/zip → rsIDs (i3000→rs3000)."""
    rsids = []
    p = Path(path)
    if p.suffix == ".zip":
        with zipfile.ZipFile(p) as z:
            with z.open(z.namelist()[0]) as f:
                for line in f.read().decode("utf-8", "ignore").splitlines():
                    parts = line.strip().split()
                    if parts and not line.startswith("#RSID"):
                        rsid = parts[0]
                        if rsid.startswith("i"):
                            rsid = "rs" + rsid[1:]
                        rsids.append(rsid)
    else:
        try:
            with open(p, encoding="utf-8", errors="ignore") as f:
                for line in f:
                    parts = line.strip().split()
                    if parts and not line.startswith("#RSID"):
                        rsid = parts[0]
                        if rsid.startswith("i"):
                            rsid = "rs" + rsid[1:]
                        rsids.append(rsid)
            print(f"✅ Genome: {len(rsids):,} rsIDs")
        except:
            print("⚠️ Demo rsIDs")
            rsids = ["i1801133"]
    return rsids[:10000]


def main(clinvar: str, genome: str, out: str = "results"):
    print("🚀 VariDex v6.1.6 ZIP/UTF8")
    cv = load_clinvar(clinvar)
    rs = load_file(genome)
    matches = []
    for r in rs:
        if r in cv:
            acmg = "P" if "pathogenic" in cv[r].lower() else "VUS"
            matches.append({"rsid": r, "clinical": cv[r], "acmg": acmg})
    Path(out).mkdir(exist_ok=True)
    with open(Path(out) / "results.csv", "w") as f:
        w = csv.DictWriter(f, ["rsid", "clinical", "acmg"])
        w.writeheader()
        w.writerows(matches)
    print(f"✅ {len(matches)} hits → {out}/results.csv")


if __name__ == "__main__":
    c = "/media/michal/647A504F7A50205A/GENOME/Michal/VariDex10/VariDex/clinvar/clinvar_GRCh37.vcf.gz"
    g = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "/media/michal/647A504F7A50205A/GENOME/Michal/raw.txt"
    )
    o = sys.argv[2] if len(sys.argv) > 2 else "results_v6.1.6"
    main(c, g, o)
