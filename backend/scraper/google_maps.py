"""Google Maps business listing extraction via Playwright."""

import asyncio
import platform
import random
import re
from typing import List, Optional
from playwright.async_api import async_playwright, Page
from backend.domain.prospect import Prospect, ProspectStatus
from backend.scraper.maps_instagram import extract_instagram_from_place_panel
from backend.scraper.maps_website import extract_official_website_from_maps_page

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
            pass

        prospects = []

        seen_keys = set()
        # Misma URL de portada en varios negocios = casi siempre error (stock/relacionados); solo la primera cuenta
        seen_cover_urls: set[str] = set()

        scroll_attempts = 0
        max_scroll_attempts = 50

        while len(prospects) < limit and scroll_attempts < max_scroll_attempts:

            cards = await self.page.query_selector_all('div[role="article"]')
            if not cards:
                cards = await self.page.query_selector_all("a.hfpxzc")

            log(f"Encontrados {len (cards )} resultados parciales. Procesando...")

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
                    # No extraer URL desde el texto de la tarjeta: suele mezclar anuncios,
                    # texto de fotos u otros negocios. La web solo desde el panel de detalle
                    # (botón "Sitio web") — ver extract_official_website_from_maps_page.

                    m_rating = re.search(r"([0-5](?:[.,][0-9])?)", card_text)
                    if m_rating:
                        raw = m_rating.group(1).replace(",", ".")
                        try:
                            rating = float(raw)
                        except ValueError:
                            rating = 0.0

                    m_reviews = re.search(
                        r"(\d[\d.,\s]*)\s*(?:reseñas|reseña|reviews?|opiniones?)",
                        card_text,
                        flags=re.IGNORECASE,
                    )
                    if m_reviews:
                        raw = m_reviews.group(1)
                        reviews_count = int(re.sub(r"\D", "", raw) or 0)
                    else:
                        m_reviews_paren = re.search(
                            r"[0-5](?:[.,][0-9])?\s*\((\d[\d.,\s]*)\)",
                            card_text,
                            flags=re.IGNORECASE,
                        )
                        if m_reviews_paren:
                            raw = m_reviews_paren.group(1)
                            reviews_count = int(re.sub(r"\D", "", raw) or 0)

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
                            r"(\+?57[\s\-]?)?(3\d{2}[\s\-]?\d{3,4}[\s\-]?\d{4})",
                            card_text,
                        )
                        if m_phone:
                            phone = m_phone.group(0).strip()

                    lat_found, lon_found = self._extract_coords(maps_url)
                    if lat_found == 0.0:
                        log(f"Sin coordenadas para: {name}")

                    detail_reviews = 0
                    detail_website = ""
                    detail_phone = ""
                    detail_instagram = ""
                    detail_photo = ""
                    try:
                        if name_el:
                            await name_el.click()
                            await asyncio.sleep(random.uniform(1.5, 2.5))
                            detail_text = await self.page.inner_text("body")

                            # --- Foto: solo hero del lugar (ver _extract_place_photo_from_maps_page) ---
                            try:
                                detail_photo = await self._extract_place_photo_from_maps_page()
                            except Exception:
                                detail_photo = ""

                            # --- Sitio web: solo botón oficial del panel (no primer http de la página) ---
                            detail_website = await extract_official_website_from_maps_page(
                                self.page
                            )

                            # --- Instagram: solo dentro del panel del lugar (no primer link global) ---
                            try:
                                ig_official = await extract_instagram_from_place_panel(
                                    self.page
                                )
                                if ig_official:
                                    detail_instagram = ig_official
                            except Exception:
                                pass

                            # --- Extract phone from detail with ARIA label ---
                            try:
                                phone_btn = await self.page.query_selector('button[data-item-id*="phone"], a[data-item-id*="phone"]')
                                if phone_btn:
                                    phone_aria = await phone_btn.get_attribute("aria-label") or ""
                                    phone_text = await phone_btn.inner_text() or ""
                                    phone_raw = phone_aria or phone_text
                                    # Clean: extract digits
                                    phone_digits = re.sub(r"[^0-9+ ]", "", phone_raw).strip()
                                    if phone_digits and len(re.sub(r"\D", "", phone_digits)) >= 7:
                                        detail_phone = phone_digits
                            except Exception:
                                pass

                            # Fallback: regex on full detail text
                            if not detail_phone:
                                m_detail_phone = re.search(
                                    r"(\+?57[\s\-]?)?(3\d{2}[\s\-]?\d{3,4}[\s\-]?\d{4})",
                                    detail_text,
                                )
                                if m_detail_phone:
                                    detail_phone = m_detail_phone.group(0).strip()

                            # --- Reviews ---
                            m_detail_reviews = re.search(
                                r"(\d[\d.,\s]*)\s*(?:reseñas|reseña|reviews?|opiniones?)",
                                detail_text,
                                flags=re.IGNORECASE,
                            )
                            if m_detail_reviews:
                                detail_reviews = int(
                                    re.sub(r"\D", "", m_detail_reviews.group(1)) or 0
                                )

                    except Exception:
                        pass

                    if not website and detail_website:
                        website = detail_website
                    if reviews_count == 0 and detail_reviews:
                        reviews_count = detail_reviews
                    if not phone and detail_phone:
                        phone = detail_phone

                    # Extract instagram handle from URL
                    instagram_url = detail_instagram
                    instagram_handle = ""
                    if instagram_url:
                        ig_match = re.search(r"instagram\.com/([^/?]+)", instagram_url)
                        if ig_match:
                            instagram_handle = ig_match.group(1)

                    # No sustituir la foto de Maps por og:image de Instagram: el link a IG a menudo
                    # es de otro negocio o genérico y copia la misma imagen a muchos leads.

                    if detail_photo and detail_photo in seen_cover_urls:
                        detail_photo = ""
                    elif detail_photo:
                        seen_cover_urls.add(detail_photo)

                    is_all = category == "*"

                    if (
                        not website
                        and not phone
                        and not detail_phone
                        and not instagram_url
                    ):
                        log(
                            f"Nota: {name} sin web/teléfono/instagram, guardando con Maps URL."
                        )

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
                        instagram_url=instagram_url,
                        instagram_handle=instagram_handle,
                        screenshot_path=detail_photo,
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

    @staticmethod
    def _cover_url_looks_usable(url: str, min_edge: int = 160) -> bool:
        """Evita miniaturas de icono; URLs googleusercontent suelen traer =wXXX-hYYY."""
        if not url or not url.strip():
            return False
        low = url.lower()
        if "googleusercontent" in low or "ggpht.com" in low:
            m = re.search(r"=w(\d+)-h(\d+)", url)
            if m:
                w, h = int(m.group(1)), int(m.group(2))
                if max(w, h) < min_edge:
                    return False
        return True

    async def _extract_place_photo_from_maps_page(self) -> str:
        """
        Portada del lugar: solo imágenes visibles del hero del panel (no el primer nodo del DOM,
        que puede ser una tarjeta oculta o duplicada).
        """
        page = self.page
        try:
            await page.wait_for_selector(
                'button[jsaction*="pane.heroHeaderImage"] img',
                timeout=8000,
            )
        except Exception:
            pass
        try:
            imgs = await page.query_selector_all(
                'button[jsaction*="pane.heroHeaderImage"] img, button[jsaction*="heroHeaderImage"] img'
            )
            for img in reversed(imgs):
                try:
                    if not await img.is_visible():
                        continue
                    src = ((await img.get_attribute("src")) or "").strip()
                    if src and self._cover_url_looks_usable(src):
                        return src
                except Exception:
                    continue
        except Exception:
            pass
        try:
            scoped = await page.query_selector(
                'div[role="region"]:has(button[jsaction*="pane.heroHeaderImage"]) img.p-img'
            )
            if scoped and await scoped.is_visible():
                src = ((await scoped.get_attribute("src")) or "").strip()
                if src and self._cover_url_looks_usable(src):
                    return src
        except Exception:
            pass
        return ""

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
