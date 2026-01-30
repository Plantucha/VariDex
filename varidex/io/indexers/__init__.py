#!/usr/bin/env python3
"""
varidex/io/indexers - Byte-offset indexing for large files

Provides efficient indexing for direct seeking in large genomic data files.
"""

from varidex.io.indexers.clinvar_xml_index import (
    build_xml_index,
    load_xml_index,
    save_xml_index,
)

__all__ = [
    "build_xml_index",
    "load_xml_index",
    "save_xml_index",
]
