"""
Ejecuta un ciclo completo del pipeline:
1) Scrape incremental
2) Enriquecimiento Instagram
3) Enriquecimiento externo
4) Health check + snapshot histórico
"""

import argparse
import subprocess
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from backend.database.db import Database

ROOT = Path(__file__).parent.parent


def run_cmd(cmd: list[str]) -> int:
    print("$", " ".join(cmd))
    p = subprocess.run(cmd, cwd=ROOT)
    return p.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one pipeline cycle")
    parser.add_argument("--city", default="Medellín")
    parser.add_argument("--scrape-category", default="*")
    parser.add_argument("--scrape-limit", type=int, default=80)
    parser.add_argument("--ig-limit", type=int, default=120)
    parser.add_argument("--ext-limit", type=int, default=120)
    parser.add_argument("--skip-scrape", action="store_true")
    parser.add_argument("--skip-ig", action="store_true")
    parser.add_argument("--skip-external", action="store_true")
    args = parser.parse_args()

    if not args.skip_scrape:
        rc = run_cmd(
            [
                "python",
                "scripts/run_scraper.py",
                "--city",
                args.city,
                "--category",
                args.scrape_category,
                "--limit",
                str(args.scrape_limit),
                "--no-ig",
            ]
        )
        if rc != 0:
            return rc

    if not args.skip_ig:
        rc = run_cmd(
            [
                "python",
                "scripts/enrich_instagram.py",
                "--limit",
                str(args.ig_limit),
                "--needs-enrichment",
                "--city",
                args.city,
            ]
        )
        if rc != 0:
            return rc

    if not args.skip_external:
        rc = run_cmd(
            [
                "python",
                "scripts/enrich_web.py",
                "--limit",
                str(args.ext_limit),
                "--city",
                args.city,
                "--sleep-ms",
                "100",
            ]
        )
        if rc != 0:
            return rc

    rc = run_cmd(["python", "scripts/health_check.py"])
    if rc != 0:
        return rc

    db = Database()
    snap = db.record_health_snapshot()
    print("Health snapshot recorded:", snap["created_at"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
