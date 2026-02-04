def write_vcf(df, path):
    """Stub writer."""
    df.to_csv(path, sep="\t", index=False)
