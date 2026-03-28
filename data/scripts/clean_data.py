import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from backend.database.db import Database


def clean_useless_leads():
    db = Database()
    with db._conn() as conn:
        print(
            "Borrando leads sin información de contacto (sin web, sin teléfono, sin instagram)..."
        )
        cur = conn.execute("""
            DELETE FROM prospects 
            WHERE (website IS NULL OR website = '') 
              AND (phone IS NULL OR phone = '') 
              AND (instagram_url IS NULL OR instagram_url = '') 
              AND (ig_email IS NULL OR ig_email = '')
              AND (ig_phone IS NULL OR ig_phone = '')
              AND status = 'scraped'
        """)
        conn.commit()
        print(f"Leads borrados: {cur .rowcount }")


if __name__ == "__main__":
    clean_useless_leads()
