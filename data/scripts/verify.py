"""
Suite rápida de verificación del proyecto:
1) Compilación de backend, scripts y rescrape_all.py
2) Pruebas (pytest, en un schema crm_test_* desechable)
3) Health check de datos (rol crm_ingest)
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def run(cmd: list[str]) -> int:
    print("\n$", " ".join(cmd))
    return subprocess.run(cmd, cwd=ROOT).returncode


def main() -> int:
    steps = [
        [sys.executable, "-m", "compileall", "-q", "backend", "data/scripts", "rescrape_all.py"],
        [sys.executable, "-m", "pytest", "-q"],
        [sys.executable, "data/scripts/health_check.py"],
    ]

    for i, cmd in enumerate(steps, start=1):
        print(f"\n=== STEP {i}/{len(steps)} ===")
        rc = run(cmd)
        if rc != 0:
            print(f"Step {i} failed with exit code {rc}")
            return rc

    print("\nVerify OK.")
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
