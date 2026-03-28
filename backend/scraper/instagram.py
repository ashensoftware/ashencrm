"""Instagram profile extraction and enrichment via Playwright."""

import asyncio
import re
import random
from urllib.parse import unquote
from typing import Optional, List
from playwright.async_api import async_playwright
from backend.domain.prospect import Prospect, ProspectStatus


class InstagramChecker:
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
                user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 14_8 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Mobile/15E148 Safari/604.1"
            )
            self.page = await self.context.new_page()

    async def find_instagram_url(self, prospect: Prospect) -> Optional[str]:
        """Busca el Instagram de un negocio en Google."""
        await self._init_browser()

        def normalize_instagram_url(raw_url: str) -> Optional[str]:
            if not raw_url:
                return None
            url = raw_url.strip()

            if "url?q=" in url:
                url = url.split("url?q=", 1)[1].split("&", 1)[0]
            url = unquote(url)

            url = url.split("#", 1)[0].split("?", 1)[0].strip()
            if "instagram.com/" not in url:
                return None
            url = url.rstrip("/")
            url_l = url.lower()

            if "/p/" in url_l or "/reels/" in url_l:
                return None
            return url

        if prospect.maps_url:
            try:
                maps_url = prospect.maps_url
                if not maps_url.startswith("http"):
                    maps_url = f"https://www.google.com{maps_url }"

                await self.page.goto(maps_url)

                for _ in range(3):
                    await asyncio.sleep(random.uniform(2, 4))

                    links = await self.page.query_selector_all(
                        'a[href*="instagram.com"]'
                    )
                    for link in links:
                        href = await link.get_attribute("href")
                        if not href:
                            continue

                        href_l = href.lower()
                        if "instagram.com/" not in href_l:
                            continue

                        if "/p/" in href_l or "/reels/" in href_l:
                            continue

                        normalized = normalize_instagram_url(href)
                        if normalized:
                            return normalized

                    await self.page.mouse.wheel(0, 1500)
            except Exception:
                pass

        search_query = f'site:instagram.com "{prospect .name }" {prospect .city }'
        url = f"https://www.google.com/search?q={search_query .replace (' ','+')}"

        await self.page.goto(url)
        await asyncio.sleep(random.uniform(1, 3))

        links = await self.page.query_selector_all("a")
        for link in links:
            href = await link.get_attribute("href")
            if (
                href
                and "instagram.com/" in href
                and "/p/" not in href
                and "/reels/" not in href
            ):
                normalized = normalize_instagram_url(href)
                if normalized:
                    return normalized
        return None

    async def check_profile(self, prospect: Prospect) -> Prospect:
        """Navega al perfil de Instagram y extrae info."""
        url = prospect.instagram_url or await self.find_instagram_url(prospect)

        if not url:
            prospect.status = ProspectStatus.READY.value
            return prospect

        prospect.instagram_url = url
        prospect.instagram_handle = url.rstrip("/").split("/")[-1]

        await self._init_browser()
        await self.page.goto(url)
        await asyncio.sleep(random.uniform(2, 4))

        bio_text = ""
        try:
            meta_og = await self.page.query_selector('meta[property="og:description"]')
            if meta_og:
                bio_text = (await meta_og.get_attribute("content")) or ""
            if not bio_text:
                meta_desc = await self.page.query_selector('meta[name="description"]')
                if meta_desc:
                    bio_text = (await meta_desc.get_attribute("content")) or ""
        except Exception:
            bio_text = ""

        try:

            website_el = await self.page.query_selector('a[href^="http"]')
            if website_el:
                website = (
                    await website_el.get_attribute("href")
                    or await website_el.inner_text()
                )
                if website:
                    website_l = website.lower()
                    if "instagram.com" not in website_l and "." in website_l:
                        prospect.ig_website = website
                        prospect.status = ProspectStatus.HAS_WEBSITE.value
        except Exception:
            pass

        if not prospect.ig_website and not prospect.website:
            prospect.status = ProspectStatus.READY.value

        if bio_text:
            prospect.ig_bio = bio_text.strip()
        else:
            try:
                bio_el = await self.page.query_selector(
                    "header section div:nth-child(3)"
                )
                if bio_el:
                    prospect.ig_bio = (await bio_el.inner_text()).strip()
            except Exception:
                pass

        contact_keywords = [
            "contact",
            "contacto",
            "email",
            "correo",
            "phone",
            "tel",
            "llamar",
        ]

        try:

            async def extract_mail_and_phone():
                extracted_email = None
                extracted_phone = None

                mail_links = await self.page.query_selector_all('a[href^="mailto:"]')
                for a in mail_links:
                    href = await a.get_attribute("href")
                    if not href:
                        continue
                    email = href.split(":", 1)[1].split("?", 1)[0].strip()
                    if email and "@" in email:
                        extracted_email = email
                        break

                tel_links = await self.page.query_selector_all('a[href^="tel:"]')
                for a in tel_links:
                    href = await a.get_attribute("href")
                    if not href:
                        continue
                    raw = href.split(":", 1)[1].strip()
                    norm = re.sub(r"[^\d+]", "", raw)
                    if norm and any(ch.isdigit() for ch in norm):
                        extracted_phone = norm
                        break

                return extracted_email, extracted_phone

            for _ in range(3):
                email_found, phone_found = await extract_mail_and_phone()
                if email_found:
                    prospect.ig_email = email_found
                if phone_found:
                    prospect.ig_phone = phone_found
                if prospect.ig_email or prospect.ig_phone:
                    break

                await self.page.mouse.wheel(0, 1200)
                await asyncio.sleep(random.uniform(1, 2))

                candidates = await self.page.query_selector_all(
                    'button, a[role="button"]'
                )
                for c in candidates[:25]:
                    try:
                        txt = (await c.inner_text()).strip().lower()
                    except Exception:
                        continue
                    if any(k in txt for k in contact_keywords):
                        try:
                            await c.click()
                            await asyncio.sleep(random.uniform(1, 2))
                            break
                        except Exception:
                            continue
        except Exception:
            pass

        try:
            page_text = await self.page.content()
            if not prospect.ig_email:

                mail_inline = re.findall(
                    r"mailto:([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})",
                    page_text,
                    flags=re.IGNORECASE,
                )
                if mail_inline:
                    prospect.ig_email = mail_inline[0]
                else:
                    email_matches = re.findall(
                        r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
                        prospect.ig_bio or page_text,
                    )
                    if email_matches:
                        prospect.ig_email = email_matches[0]

            if not prospect.ig_phone:
                tel_inline = re.findall(
                    r"tel:([^\"\\s>]+)", page_text, flags=re.IGNORECASE
                )
                for raw in tel_inline:
                    norm = re.sub(r"[^\d+]", "", raw)
                    if norm and any(ch.isdigit() for ch in norm):
                        prospect.ig_phone = norm
                        break
                if not prospect.ig_phone:
                    phone_matches = re.findall(
                        r"(?:\+?\d[\d\s\-]{7,}\d)", prospect.ig_bio or page_text
                    )
                    if phone_matches:
                        prospect.ig_phone = phone_matches[0]
        except Exception:
            pass

        try:
            page_text = await self.page.content()

            m_follow = re.search(
                r"([0-9][0-9\.,]*)\s*(seguidores|followers)",
                page_text,
                flags=re.IGNORECASE,
            )
            if m_follow:
                raw = m_follow.group(1)
                prospect.ig_followers = int(re.sub(r"\D", "", raw) or "0")
            else:

                m_short = re.search(
                    r"([0-9]+(?:[\,\.][0-9]+)?)\s*([kKmM]|mil)\s*(seguidores|followers)",
                    page_text,
                    flags=re.IGNORECASE,
                )
                if m_short:
                    num_raw = m_short.group(1).replace(",", ".")
                    suffix = m_short.group(2).lower()
                    num = float(num_raw)
                    if suffix == "k":
                        prospect.ig_followers = int(num * 1000)
                    elif suffix == "mil":
                        prospect.ig_followers = int(num * 1000)
                    elif suffix == "m":
                        prospect.ig_followers = int(num * 1000000)
        except Exception:
            pass

        return prospect

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
