"""
Ejecuta la fase Lovable (Generator) para prospectos en estado ``ready``.

Flujo: prompt -> automatizacion Playwright en lovable.dev -> screenshot -> DB (demo_created).

Uso:
  # Simular (solo lista cuantos hay)
  python scripts/run_generator.py --limit 5

  # Ejecutar de verdad (requiere sesion logueada en config/sessions/account_*)
  set LOVABLE_HEADLESS=false   # primera vez, recomendado
  python scripts/run_generator.py --limit 1 --execute
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from backend.database.db import Database
from backend.generator.service import GeneratorService


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fase Lovable: generar demos para leads ready"
    )
    parser.add_argument(
        "--limit", type=int, default=5, help="Maximo de prospectos ready a procesar"
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Sin este flag: solo muestra cuantos leads ready hay (dry-run)",
    )
    args = parser.parse_args()

    db = Database()
    gen = GeneratorService(db)
    ready = db.get_prospects(status="ready", limit=args.limit)

    print(f"Leads listos (status=ready): {len (ready )} (limite {args .limit })")
    if not ready:
        print(
            "Nada que generar. Marca prospectos como 'ready' desde el dashboard o la API."
        )
        return

    if not args.execute:
        print(
            "Dry-run: no se abre el navegador. Usa --execute para generar en Lovable."
        )
        for p in ready:
            print(f"  - {p .name } | {p .category } | {p .city }")
        return

    for p in ready:
        print(f"[Generator] Procesando: {p .name }")
        try:
            result = await gen.run_full_generation(p)
            print(f"[Generator] Resultado: {result }")
        except Exception as e:
            print(f"[Generator] Error: {e }")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    asyncio.run(main())
