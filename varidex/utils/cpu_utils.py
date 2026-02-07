"""
CPU Core Detection and Worker Optimization
Auto-detects cores and calculates optimal workers for different task types
"""
import os
from typing import Dict


def get_cpu_info() -> Dict[str, int]:
    """Detect CPU cores and calculate optimal workers"""
    logical_cores = os.cpu_count() or 4
    physical_cores = max(1, logical_cores // 2)

    return {
        "logical_cores": logical_cores,
        "physical_cores": physical_cores,
    }


def get_optimal_workers(task_type: str = "cpu_bound") -> int:
    """
    Calculate optimal worker count based on task type

    Args:
        task_type: "cpu_bound", "io_bound", or "mixed"

    Returns:
        Optimal number of workers

    Rules (for CPU-intensive genomic data):
        - cpu_bound: physical cores - 1 (leave overhead for OS)
        - io_bound: 2x logical cores (network/disk waits allow oversubscription)
        - mixed: 70% of logical cores (balance)
    """
    info = get_cpu_info()
    logical = info["logical_cores"]
    physical = info["physical_cores"]

    if task_type == "cpu_bound":
        workers = max(1, physical - 1)
    elif task_type == "io_bound":
        workers = max(4, logical * 2)
    elif task_type == "mixed":
        workers = max(2, int(logical * 0.7))
    else:
        workers = logical

    return workers


def print_cpu_info():
    """Print CPU detection summary"""
    info = get_cpu_info()

    print("🖥️  CPU Detection:")
    print(f"   Logical cores: {info['logical_cores']}")
    print(f"   Physical cores (est): {info['physical_cores']}")
    print()
    print("📊 Recommended Workers:")
    print(f"   CPU-bound: {get_optimal_workers('cpu_bound')} workers")
    print(f"   I/O-bound: {get_optimal_workers('io_bound')} workers")
    print(f"   Mixed: {get_optimal_workers('mixed')} workers")


if __name__ == "__main__":
    print_cpu_info()
