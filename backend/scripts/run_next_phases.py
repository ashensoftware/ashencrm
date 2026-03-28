"""
Ejecuta siguientes fases del pipeline:
- Generator (si status=ready)
- Outreach (si status=demo_created)

Por defecto corre en dry-run para no disparar envíos reales.
"""

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from backend.database.db import Database
from backend.generator.service import GeneratorService
from backend.outreach.service import OutreachService


async def main():
    parser = argparse.ArgumentParser(
        description="Run next pipeline phases (generator/outreach)"
    )
    parser.add_argument("--generator-limit", type=int, default=10)
    parser.add_argument("--outreach-limit", type=int, default=10)
    parser.add_argument(
        "--execute", action="store_true", help="Sin este flag: solo dry-run"
    )
    args = parser.parse_args()

    db = Database()
    gen = GeneratorService(db)
    out = OutreachService(db)

    ready = db.get_prospects(status="ready", limit=args.generator_limit)
    demo_created = db.get_prospects(status="demo_created", limit=args.outreach_limit)

    print(f"Ready leads (generator): {len (ready )}")
    print(f"Demo-created leads (outreach): {len (demo_created )}")

    if not args.execute:
        print("Dry-run mode: no se ejecuta generator/outreach real.")
        return

    for p in ready:
        print("Generating for:", p.name)
        try:
            result = await gen.run_full_generation(p)
            print("Result:", result)
        except Exception as e:
            print("Generator error:", e)

    for p in demo_created:
        print("Sending outreach for:", p.name)
        try:
            result = await out.send_proposal(p)
            print("Result:", result)
        except Exception as e:
            print("Outreach error:", e)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    asyncio.run(main())
