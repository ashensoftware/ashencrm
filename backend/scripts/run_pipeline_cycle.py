"""
Ejecuta un ciclo completo del pipeline:
1) Scrape incremental
2) Enriquecimiento Instagram
3) Enriquecimiento externo
4) Health check

Cada paso es un script local con el rol crm_ingest (DATABASE_INGEST_URL). El
snapshot histórico de salud ya no se graba aquí: crm_ingest no escribe en
health_history; se graba desde la API (POST /api/prospects/health/record).
"""

import argparse
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
RUN_SCRAPER = REPO / "backend" / "scripts" / "run_scraper.py"
ENRICH_INSTAGRAM = REPO / "data" / "scripts" / "enrich_instagram.py"
ENRICH_WEB = REPO / "data" / "scripts" / "enrich_web.py"
HEALTH_CHECK = REPO / "data" / "scripts" / "health_check.py"


def run_cmd(script: Path, *args: str) -> int:
    cmd = [sys.executable, str(script), *args]
    print("$", " ".join(cmd))
    return subprocess.run(cmd, cwd=REPO).returncode


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
            RUN_SCRAPER,
            "--city", args.city,
            "--category", args.scrape_category,
            "--limit", str(args.scrape_limit),
            "--no-ig",
        )
        if rc != 0:
            return rc

    if not args.skip_ig:
        rc = run_cmd(
            ENRICH_INSTAGRAM,
            "--limit", str(args.ig_limit),
            "--needs-enrichment",
            "--city", args.city,
        )
        if rc != 0:
            return rc

    if not args.skip_external:
        rc = run_cmd(
            ENRICH_WEB,
            "--limit", str(args.ext_limit),
            "--city", args.city,
            "--sleep-ms", "100",
        )
        if rc != 0:
            return rc

    return run_cmd(HEALTH_CHECK)


if __name__ == "__main__":
    raise SystemExit(main())
