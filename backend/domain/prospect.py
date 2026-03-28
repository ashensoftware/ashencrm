"""Prospect entity and status enum for the lead pipeline."""

from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from typing import Optional
import json


class ProspectStatus(str, Enum):
    SCRAPED = "scraped"
    WAITING = "waiting"
    IG_CHECKED = "ig_checked"
    HAS_WEBSITE = "has_website"
    READY = "ready"
    PROMPT_GPT = "prompt_gpt"
    CREATING_DEMO = "creating_demo"
    DEMO_CREATED = "demo_created"
    CONTACTED = "contacted"
    CLIENT_WON = "client_won"
    RESPONDED = "responded"
    SKIPPED = "skipped"
    REJECTED = "rejected"


@dataclass
class Prospect:
    name: str
    category: str
    address: str = ""
    city: str = ""
    phone: str = ""
    website: str = ""
    rating: float = 0.0
    reviews_count: int = 0
    maps_url: str = ""
    latitude: float = 0.0
    longitude: float = 0.0
    instagram_url: str = ""
    instagram_handle: str = ""
    ig_followers: int = 0
    ig_bio: str = ""
    ig_email: str = ""
    ig_phone: str = ""
    ig_website: str = ""
    demo_url: str = ""
    screenshot_path: str = ""
    lovable_account_used: str = ""
    prompt_used: str = ""
    whatsapp_message: str = ""
    status: str = ProspectStatus.SCRAPED.value
    scraped_at: str = ""
    contacted_at: Optional[str] = None
    is_contacted: bool = False
    notes: str = ""

    def __post_init__(self):
        if not self.scraped_at:
            self.scraped_at = datetime.now().isoformat()

    def has_existing_website(self) -> bool:
        return bool(self.website or self.ig_website)

    def get_best_phone(self) -> str:
        return self.phone or self.ig_phone or ""

    def get_best_contact(self) -> dict:
        return {
            "phone": self.get_best_phone(),
            "email": self.ig_email,
            "instagram": self.instagram_url,
        }

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    @classmethod
    def from_dict(cls, data: dict) -> "Prospect":
        fields = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        return cls(**fields)
