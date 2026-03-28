"""Google Maps business listing extraction via Playwright."""

import asyncio
import platform
import random
import re
from typing import List, Optional
from playwright.async_api import async_playwright, Page
from backend.domain.prospect import Prospect, ProspectStatus

if platform.system() == "Windows":
    try:
        if not isinstance(
            asyncio.get_event_loop_policy(), asyncio.WindowsProactorEventLoopPolicy
        ):
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    except Exception:
        pass


class GoogleMapsScraper:
    def __init__(self, headless: bool = True):
        self.headless = headless
        self._playwright = None
        self.browser = None
        self.context = None
        self.page = None

    async def _init_browser(self):
        if not self._playwright:
            self._playwright = await async_playwright().start()
            self.browser = await self._playwright.chromium.launch(
                headless=self.headless
            )
            self.context = await self.browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            self.page = await self.context.new_page()

    async def search(
        self,
        category: str,
        city: str = "Medellín",
        limit: int = 50,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        zoom: int = 16,
        log_callback: Optional[callable] = None,
    ) -> List[Prospect]:
        def log(msg):
            if log_callback:
                log_callback(msg)
            else:
                print(msg)

        log(f"Iniciando navegador para buscar {category }...")
        await self._init_browser()

        if lat and lon:

            search_query = (
                category
                if category != "*"
                else "restaurantes, tiendas, servicios, salud, oficinas"
            )
            url = f"https://www.google.com/maps/search/{search_query .replace (' ','+')}/@{lat },{lon },{zoom }z"
        else:
            search_query = (
                f"{category } en {city }"
                if category != "*"
                else f"restaurantes, tiendas, servicios, salud, oficinas en {city }"
            )
            url = (
                f"https://www.google.com/maps/search/{search_query .replace (' ','+')}"
            )

        log(f"Navegando a: {url }")
        await self.page.goto(url)
        await asyncio.sleep(5)

        await self.page.screenshot(path="data/debug_initial.png")
        print("Screenshot inicial guardado en data/debug_initial.png")

        try:
            consent_btn = await self.page.query_selector(
                'button[aria-label="Aceptar todo"], button[aria-label="Aceptar"], button:has-text("Aceptar todo")'
            )
            if consent_btn:
                log("Manejando consentimiento de cookies...")
                await consent_btn.click()
                await asyncio.sleep(3)
        except:
            pass

        try:
            await self.page.wait_for_selector('div[role="feed"]', timeout=15000)
            log("Panel de resultados cargado.")
        except:
            log("Timeout esperando resultados. Intentando parseo directo.")
            await self.page.screenshot(path="data/debug_no_feed.png")

        prospects = []

        seen_keys = set()

        scroll_attempts = 0
        max_scroll_attempts = 50

        while len(prospects) < limit and scroll_attempts < max_scroll_attempts:

            cards = await self.page.query_selector_all('div[role="article"]')
            if not cards:
                cards = await self.page.query_selector_all("a.hfpxzc")

            log(f"Encontrados {len (cards )} resultados parciales. Procesando...")

            if not cards:

                await self.page.screenshot(
                    path=f"data/debug_no_cards_{scroll_attempts }.png"
                )

            for card in cards:
                if len(prospects) >= limit:
                    break

                try:

                    name_el = await card.query_selector(".hfpxzc")
                    if name_el:
                        name = await name_el.get_attribute("aria-label")
                        maps_url = await name_el.get_attribute("href")
                    else:

                        name = await card.get_attribute("aria-label")
                        maps_url = await card.get_attribute("href")

                    if not name:
                        continue

                    key = maps_url or name
                    if key in seen_keys:
                        continue

                    card_text = await card.inner_text()
                    lines = [l.strip() for l in card_text.split("\n") if l.strip()]

                    native_cat = ""
                    if len(lines) > 1:
                        if re.search(r"\d\.\d\s\(", lines[1]):
                            native_cat = lines[2] if len(lines) > 2 else ""
                        else:
                            native_cat = lines[1]

                    if " · " in native_cat:
                        native_cat = native_cat.split(" · ")[0]

                    rating = 0.0
                    reviews_count = 0
                    website = ""

                    m_rating = re.search(r"([0-5](?:[\\.,][0-9])?)", card_text)
                    if m_rating:
                        raw = m_rating.group(1).replace(",", ".")
                        try:
                            rating = float(raw)
                        except ValueError:
                            rating = 0.0

                    m_reviews = re.search(
                        r"([0-9][0-9\\.,\\s]*)\\s*(?:rese\\u00f1as|rese\\u00f1a|rese\\u00f1a[s]?|reviews?|review|opinion(?:es)?|rese\\u00f1a?s?)",
                        card_text,
                        flags=re.IGNORECASE,
                    )
                    if m_reviews:
                        raw = m_reviews.group(1)
                        reviews_count = int(re.sub(r"\\D", "", raw) or 0)
                    else:

                        m_reviews_paren = re.search(
                            r"[0-5](?:[\\.,][0-9])?\\s*\\(([0-9][0-9\\.,\\s]*)\\)",
                            card_text,
                            flags=re.IGNORECASE,
                        )
                        if m_reviews_paren:
                            raw = m_reviews_paren.group(1)
                            reviews_count = int(re.sub(r"\\D", "", raw) or 0)

                    urls = re.findall(r"https?://[^\\s\\)\\]]+", card_text)
                    for u in urls:
                        u_l = u.lower()
                        if "google.com/maps" in u_l:
                            continue
                        if "instagram.com" in u_l:
                            continue
                        if "facebook.com" in u_l:
                            continue
                        if "duckduckgo.com" in u_l:
                            continue
                        website = u
                        break

                    if not website:
                        m_www = re.search(
                            r"\\b(www\\.[A-Za-z0-9\\.-]+\\.[A-Za-z]{2,}(?:/[^\\s\\)\\]]*)?)",
                            card_text,
                        )
                        if m_www:
                            website = "https://" + m_www.group(1).rstrip(".")

                    phone = ""
                    address = city
                    for line in lines:
                        cl_line = re.sub(r"[^0-9+]", "", line)
                        if (line.startswith("+57") or line.startswith("3")) and 10 <= len(cl_line) <= 13:
                            phone = line
                        elif city.lower() in line.lower() or any(
                            k in line.lower()
                            for k in ["cl ", "cl.", "cra", "av.", "calle"]
                        ):
                            address = line

                    if not phone:
                        m_phone = re.search(
                            r"(\\+?57[\\s\\-]?)?(3[0-9][\\s\\-]?[0-9]{3}[\\s\\-]?[0-9]{4})",
                            card_text,
                        )
                        if m_phone:
                            phone = m_phone.group(0).strip()

                    lat_found, lon_found = self._extract_coords(maps_url)
                    if lat_found == 0.0:
                        log(f"Sin coordenadas para: {name }")

                    detail_reviews = 0
                    detail_website = ""
                    detail_phone = ""
                    try:
                        if name_el:
                            await name_el.click()
                            await asyncio.sleep(random.uniform(1.5, 2.5))
                            detail_text = await self.page.inner_text("body")

                            detail_links = await self.page.query_selector_all(
                                'a[data-item-id*="authority"], a[aria-label*="Sitio web"], a[aria-label*="Website"], a[href^="http"]'
                            )
                            for lnk in detail_links:
                                href = await lnk.get_attribute("href")
                                if not href:
                                    continue
                                href_l = href.lower()
                                if "google.com" in href_l:
                                    continue
                                if "instagram.com" in href_l:
                                    continue
                                if "facebook.com" in href_l:
                                    continue
                                if "duckduckgo.com" in href_l:
                                    continue
                                if re.search(r"\.[a-z]{2,}(/|$)", href_l):
                                    detail_website = href.rstrip(".")
                                    break

                            m_detail_reviews = re.search(
                                r"([0-9][0-9\\.,\\s]*)\\s*(?:reseñas|rese\\u00f1as|reviews?|opiniones?)",
                                detail_text,
                                flags=re.IGNORECASE,
                            )
                            if m_detail_reviews:
                                detail_reviews = int(
                                    re.sub(r"\\D", "", m_detail_reviews.group(1)) or 0
                                )

                            m_detail_phone = re.search(
                                r"(\\+?57[\\s\\-]?)?(3[0-9][\\s\\-]?[0-9]{3}[\\s\\-]?[0-9]{4})",
                                detail_text,
                            )
                            if m_detail_phone:
                                detail_phone = m_detail_phone.group(0).strip()
                    except Exception:
                        pass

                    if not website and detail_website:
                        website = detail_website
                    if reviews_count == 0 and detail_reviews:
                        reviews_count = detail_reviews
                    if not phone and detail_phone:
                        phone = detail_phone

                    is_all = category == "*"

                    if (
                        not website
                        and not phone
                        and not detail_phone
                        and "instagram.com" not in maps_url
                    ):

                        log(
                            f"Descartando {name } por no tener web, teléfono ni instagram."
                        )
                        continue

                    prospect = Prospect(
                        name=name,
                        category=category,
                        address=address,
                        city=city,
                        phone=phone,
                        website=website,
                        rating=rating,
                        reviews_count=reviews_count,
                        maps_url=maps_url,
                        latitude=lat_found,
                        longitude=lon_found,
                        notes=native_cat if is_all else "",
                        status=ProspectStatus.SCRAPED.value,
                    )

                    prospects.append(prospect)
                    seen_keys.add(key)
                    log(f"Scrapeado: {name }")
                except Exception as e:
                    log(f"Error en tarjeta: {str (e )}")

            print(f"Haciendo scroll ({scroll_attempts }/{max_scroll_attempts })...")
            feed = await self.page.query_selector('div[role="feed"]')
            if feed:
                await feed.evaluate("el => el.scrollTop += 2000")
            else:
                await self.page.mouse.wheel(0, 2000)

            await asyncio.sleep(2)
            scroll_attempts += 1

            end_msg = await self.page.query_selector(
                'text="Has llegado al final de la lista", text="Final de la lista"'
            )
            if end_msg:
                print("Fin alcanzado.")
                break

        return prospects

    def _extract_coords(self, url: str) -> tuple[float, float]:
        """Extrae latitud y longitud de un URL de Google Maps."""
        if not url:
            return 0.0, 0.0

        match_at = re.search(r"@(-?\d+\.\d+),(-?\d+\.\d+)", url)
        if match_at:
            return float(match_at.group(1)), float(match_at.group(2))

        match_bang = re.search(r"!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)", url)
        if match_bang:
            return float(match_bang.group(1)), float(match_bang.group(2))

        return 0.0, 0.0

    async def close(self):
        """Cierra el navegador."""
        try:
            if self.context:
                await self.context.close()
                self.context = None
            if self.browser:
                await self.browser.close()
                self.browser = None
            if self._playwright:
                await self._playwright.stop()
                self._playwright = None
        except Exception:
            pass
