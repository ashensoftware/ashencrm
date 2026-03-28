"""
Suite rápida de debug del proyecto:
1) Compilación de archivos clave
2) Tests unitarios
3) Health check de datos
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent


def run(cmd: list[str]) -> int:
    print("\n$", " ".join(cmd))
    p = subprocess.run(cmd, cwd=ROOT)
    return p.returncode


def main() -> int:
    steps = [
        [
            "python",
            "-m",
            "py_compile",
            "src/scraper/google_maps.py",
            "src/scraper/instagram.py",
            "src/database/db.py",
            "scripts/enrich_instagram.py",
            "scripts/enrich_maps.py",
            "scripts/enrich_web.py",
            "scripts/run_pipeline_cycle.py",
            "scripts/run_pipeline_scheduler.py",
            "scripts/run_next_phases.py",
            "scripts/run_generator.py",
            "src/generator/lovable.py",
            "src/generator/service.py",
            "scripts/health_check.py",
        ],
        ["python", "-m", "unittest", "discover", "-s", "tests", "-p", "test*.py", "-q"],
        ["python", "scripts/health_check.py"],
    ]

    for i, cmd in enumerate(steps, start=1):
        print(f"\n=== STEP {i }/{len (steps )} ===")
        rc = run(cmd)
        if rc != 0:
            print(f"Step {i } failed with exit code {rc }")
            return rc

    print("\nVerify OK.")
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
