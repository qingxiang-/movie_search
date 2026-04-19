#!/usr/bin/env python3
"""
Performance Report Generator
Generates HTML performance report from archived recommendations.

Usage:
    python performance_report.py
"""

import logging
from utils.performance_tracker import performance_tracker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Generate performance report from all archived recommendations."""
    logger.info("Generating performance report from archived recommendations...")

    report_path = performance_tracker.generate_performance_report()

    if report_path:
        logger.info(f"✅ Performance report generated: {report_path}")
        print(f"\n✅ Performance report generated: {report_path}")
    else:
        logger.error("❌ Failed to generate performance report")
        print("\n❌ Failed to generate performance report")

if __name__ == "__main__":
    main()
