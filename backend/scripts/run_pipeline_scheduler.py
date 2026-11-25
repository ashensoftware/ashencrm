"""
Scheduler simple del pipeline (loop con intervalo fijo).
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CYCLE = REPO / "backend" / "scripts" / "run_pipeline_cycle.py"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run pipeline cycle repeatedly")
    parser.add_argument(
        "--interval-min", type=int, default=120, help="Intervalo entre ciclos"
    )
    parser.add_argument("--max-cycles", type=int, default=0, help="0 = infinito")
    args = parser.parse_args()

    cycles = 0
    while True:
        cycles += 1
        print(f"\n=== PIPELINE CYCLE {cycles } ===")
        rc = subprocess.run([sys.executable, str(CYCLE)], cwd=REPO).returncode
        print("Cycle rc:", rc)
        if args.max_cycles and cycles >= args.max_cycles:
            break
        time.sleep(max(1, args.interval_min) * 60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
