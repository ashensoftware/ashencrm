"""Cliente de Places API (New). No llama a la red si no hay clave ni transporte de prueba.

Endpoint documentado: https://places.googleapis.com/v1/places:searchText
"""

from __future__ import annotations

from typing import Any, Callable

import httpx

PLACES_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
FIELD_MASK = "places.id,places.displayName,places.formattedAddress,places.nationalPhoneNumber,places.websiteUri"


class PlacesError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


class GooglePlacesClient:
    def __init__(self, api_key: str, transport: Callable[..., httpx.Response] | None = None, timeout: float = 8.0):
        self.api_key = api_key
        self.timeout = timeout
        self._transport = transport

    def search_text(self, query: str, *, max_results: int = 10) -> list[dict[str, Any]]:
        if not self.api_key:
            raise PlacesError("missing_api_key", "GOOGLE_PLACES_API_KEY no está configurada")
        if not query.strip():
            raise PlacesError("invalid_query", "La consulta está vacía")
        payload = {"textQuery": query, "maxResultCount": max(1, min(max_results, 20))}
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": FIELD_MASK,
        }
        if self._transport is not None:
            response = self._transport("POST", PLACES_SEARCH_URL, json=payload, headers=headers, timeout=self.timeout)
        else:
            try:
                response = httpx.post(PLACES_SEARCH_URL, json=payload, headers=headers, timeout=self.timeout)
            except httpx.TimeoutException as exc:
                raise PlacesError("timeout", "Tiempo de espera agotado en Places") from exc
            except httpx.HTTPError as exc:
                raise PlacesError("transport", "No se pudo contactar Places") from exc
        if response.status_code == 429:
            raise PlacesError("rate_limited", "Places aplicó un límite de uso")
        if response.status_code >= 500:
            raise PlacesError("unavailable", "Places no está disponible")
        if response.status_code != 200:
            raise PlacesError("rejected", "Places rechazó la consulta")
        body = response.json()
        places = body.get("places") if isinstance(body, dict) else None
        if not isinstance(places, list):
            return []
        return [item for item in places if isinstance(item, dict) and item.get("id")]
