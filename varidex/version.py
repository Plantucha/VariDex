#!/usr/bin/env python3
"""varidex.version - Version Information"""

# Export both 'version' and '__version__' for compatibility
__all__ = ["version", "__version__", "get_version", "get_full_version_info"]

version = "6.0.0"
__version__ = version  # Some modules expect __version__

versions = {
    "package": "6.0.0",
    "core": "6.0.0",
    "core.classifier": "6.0.0",
    "io": "6.0.0",
    "io.loader": "6.0.0",
    "reports.generator": "6.0.0",
    "pipeline": "6.0.0",
    "utils.helpers": "6.0.0"
}

acmg_version = "2015"
acmg_reference = "Richards et al. 2015, PMID 25741868"
build_date = "2026-01-20"

def get_version(component="package"):
    """Get version for component."""
    return versions.get(component, version)

def get_full_version_info():
    """Get complete version info."""
    return {
        "package_version": version,
        "build_date": build_date,
        "acmg_version": acmg_version,
        "acmg_reference": acmg_reference,
    }

if __name__ == "__main__":
    print("VariDex v" + version)
    print("ACMG " + acmg_version)
