"""
Descarta leads sin ningún dato de contacto (sin web, teléfono, Instagram, email).

No borra: los marca `rejected` (crm_ingest no tiene DELETE, y así queda rastro y
se pueden recuperar). Por defecto solo cuenta; `--apply` los marca.

  python data/scripts/clean_data.py           # ensayo
  python data/scripts/clean_data.py --apply   # marca como rejected
"""

import argparse
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from backend.infrastructure.persistence.ingest import ingest_repository

USELESS = """
    (website IS NULL OR website = '')
    AND (phone IS NULL OR phone = '')
    AND (instagram_url IS NULL OR instagram_url = '')
    AND (ig_email IS NULL OR ig_email = '')
    AND (ig_phone IS NULL OR ig_phone = '')
    AND status = 'scraped'
"""


def clean_useless_leads(apply: bool) -> int:
    db = ingest_repository()
    with db._conn() as conn:
        if not apply:
            n = conn.execute(f"SELECT COUNT(*) AS n FROM prospects WHERE {USELESS}").fetchone()["n"]
            print(f"Ensayo: {n} leads sin contacto se marcarían como rejected. Repite con --apply.")
            return n
        cur = conn.execute(
            f"UPDATE prospects SET status = 'rejected' WHERE {USELESS}"
        )
        print(f"Leads marcados como rejected: {cur.rowcount}")
        return cur.rowcount


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument("--apply", action="store_true", help="Marca los leads (sin esto solo cuenta)")
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    clean_useless_leads(args.apply)
