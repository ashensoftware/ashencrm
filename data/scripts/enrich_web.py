"""
Enriquecimiento externo de leads usando resultados web (DuckDuckGo HTML).

Objetivo:
- Aumentar cobertura de `website`, `ig_email`, `ig_phone` sin depender de DOM de Maps/IG.
"""

import argparse
import re
import sqlite3
import sys
import time
from pathlib import Path
from urllib.parse import quote_plus, unquote, urlparse
from urllib.request import Request, urlopen

sys.path.append(str(Path(__file__).parent.parent))

from backend.config.settings import settings
from backend.core.maps_website import website_plausible_for_business
from backend.database.db import Database
from backend.scraper.models import Prospect

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def fetch_url(url: str, timeout: int = 20) -> str:
    req = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def is_external_business_domain(url: str) -> bool:
    try:
        host = (urlparse(url).netloc or "").lower()
    except Exception:
        return False
    blocked = [
        "google.",
        "gstatic.",
        "youtube.",
        "youtu.be",
        "facebook.",
        "instagram.",
        "tiktok.",
        "twitter.",
        "x.com",
        "linkedin.",
        "whatsapp.",
        "wikipedia.",
    ]
    return bool(host) and not any(b in host for b in blocked)


def extract_result_links(ddg_html: str) -> list[str]:
    """
    Extrae links de resultados en DuckDuckGo HTML.
    Suelen venir como:
      /l/?kh=-1&uddg=<url-encoded>
    """
    links = []
    for m in re.finditer(r'href="(/l/\?[^"]*uddg=([^"&]+)[^"]*)"', ddg_html):
        encoded = m.group(2)
        url = unquote(encoded)
        if url.startswith("http"):
            links.append(url)

    if not links:
        for m in re.finditer(r'href="(https?://[^"]+)"', ddg_html):
            links.append(m.group(1))

    out = []
    seen = set()
    for u in links:
        if u in seen:
            continue
        seen.add(u)
        out.append(u)
    return out


def extract_email(text: str) -> str:
    m = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
    return m.group(0) if m else ""


def extract_phone(text: str) -> str:

    m = re.search(r"(?:\+?57[\s\-]?)?(3[0-9][\s\-]?[0-9]{3}[\s\-]?[0-9]{4})", text)
    if m:
        return re.sub(r"[^\d+]", "", m.group(0))

    m2 = re.search(r"(?:\+?\d[\d\s\-]{8,}\d)", text)
    if m2:
        return re.sub(r"[^\d+]", "", m2.group(0))
    return ""


def choose_website(links: list[str]) -> str:
    for u in links:
        if is_external_business_domain(u):
            return u
    return ""


def enrich_prospect_external(p: Prospect) -> dict:
    query = f"{p .name } {p .city or 'Medellín'}"
    q = quote_plus(query)
    search_url = f"https://duckduckgo.com/html/?q={q }"

    patch = {}
    try:
        html = fetch_url(search_url, timeout=20)
    except Exception:
        return patch

    links = extract_result_links(html)

    if not p.website:
        website = choose_website(links)
        if website and website_plausible_for_business(website, p.name):
            patch["website"] = website

    if not p.ig_email:
        email = extract_email(html)
        if email:
            patch["ig_email"] = email
    if not p.ig_phone:
        phone = extract_phone(html)
        if phone:
            patch["ig_phone"] = phone

    target_url = patch.get("website") or p.website
    if target_url and ((not p.ig_email) or (not p.ig_phone)):
        try:
            home = fetch_url(target_url, timeout=20)
            if not p.ig_email and "ig_email" not in patch:
                email2 = extract_email(home)
                if email2:
                    patch["ig_email"] = email2
            if not p.ig_phone and "ig_phone" not in patch:
                phone2 = extract_phone(home)
                if phone2:
                    patch["ig_phone"] = phone2
        except Exception:
            pass

    return patch


def load_candidates(db: Database, limit: int, city: str | None) -> list[Prospect]:
    with db._get_conn() as conn:
        query = """
            SELECT * FROM prospects
            WHERE
                (
                    website IS NULL OR website = ''
                    OR ig_email IS NULL OR ig_email = ''
                    OR ig_phone IS NULL OR ig_phone = ''
                )
                AND status IN ('scraped', 'ready', 'contacted')
        """
        params = []
        if city:
            query += " AND city = ?"
            params.append(city)
        query += " ORDER BY RANDOM() LIMIT ?"
        params.append(limit)
        rows = conn.execute(query, params).fetchall()
    return [Prospect.from_dict(dict(r)) for r in rows]


def main():
    parser = argparse.ArgumentParser(
        description="Enriquece website/email/phone con señales externas."
    )
    parser.add_argument(
        "--limit", type=int, default=100, help="Cantidad de prospectos a procesar"
    )
    parser.add_argument("--city", default=None, help="Filtrar por ciudad")
    parser.add_argument(
        "--sleep-ms",
        type=int,
        default=300,
        help="Pausa entre prospectos para evitar bloqueo",
    )
    args = parser.parse_args()

    db = Database()
    candidates = load_candidates(db, args.limit, args.city)
    print(f"Candidatos: {len (candidates )}")

    updated = 0
    for idx, p in enumerate(candidates, start=1):
        patch = enrich_prospect_external(p)
        if patch:
            db.patch_prospect(p.name, p.address, patch)
            updated += 1
            print(
                f"[{idx }/{len (candidates )}] Updated {p .name }: {list (patch .keys ())}"
            )
        else:
            print(f"[{idx }/{len (candidates )}] No data {p .name }")
        time.sleep(max(0, args.sleep_ms) / 1000.0)

    print(f"Done. Updated: {updated }/{len (candidates )}")
    print(db.stats())


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    main()
