import pandas as pd

df = pd.read_csv("AlphaMissense_hg38.tsv.gz", sep="\t", nrows=100000)
df.to_csv("data/AlphaMissense_formatted.tsv", sep="\t", index=False)
print("✅ Formatted!")
