import pandas as pd
import numpy as np


def convert_to_1based(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in ["position", "POS"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int) + 1
    return df


def convert_to_0based(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in ["position", "POS"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int) - 1
    return df
