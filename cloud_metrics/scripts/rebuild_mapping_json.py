# cloud_metrics/scripts/rebuild_mapping_json.py

from __future__ import annotations

import sys
from pathlib import Path

from cloud_metrics.exporters.rebuild_mapping_json import rebuild_mapping

def main():
    out = rebuild_mapping()
    print(f"metric_mapping.json rebuilt at: {out}")

if __name__ == "__main__":
    main()

