#!/usr/bin/env python3
"""
varidex/io/indexers - XML Indexing Module

Provides byte-offset indexing for fast ClinVar XML parsing.
Enables 30-60s load times with <500MB RAM usage.
"""

from varidex.io.indexers.clinvar_xml_index import (
    build_xml_index,
    get_index_path,
    load_xml_index,
)

__all__ = [
    "build_xml_index",
    "load_xml_index",
    "get_index_path",
]
