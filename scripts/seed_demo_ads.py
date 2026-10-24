#!/usr/bin/env python3
"""Seed first-party display ads (Home wall + Storylines list). Audio ads are a separate system."""

from __future__ import annotations

import sys
from urllib.parse import urlparse

from pymongo import MongoClient

URI = "mongodb://127.0.0.1:27017"
DB = "cnews"


def _require_local(uri: str) -> None:
    """Demo data (real-brand ads, fake stories) must never reach a shared database."""
    host = urlparse(uri).hostname
    if uri.startswith("mongodb+srv://") or host not in {"127.0.0.1", "localhost", "::1"}:
        sys.exit(f"Refusing to seed demo data into a non-local MongoDB ({host}).")


ADS = [
    {
        "adId": "display_demo_1",
        "advertiser": "VIA Rail",
        "title": "Weekend trains from $49 — see Canada by rail",
        "clickUrl": "https://www.viarail.ca/",
        "imageKey": "local/ads/display/ad_demo_1.jpg",
        "imageAspect": 0.74,
        "active": True,
        "slot": "home_wall",
        "slots": ["home_wall"],
    },
    {
        "adId": "display_demo_2",
        "advertiser": "CAA",
        "title": "Roadside cover that actually shows up",
        "clickUrl": "https://www.caa.ca/",
        "imageKey": "local/ads/display/ad_demo_2.jpg",
        "imageAspect": 0.68,
        "active": True,
        "slot": "storylines_list",
        "slots": ["home_wall", "storylines_list"],
    },
    {
        "adId": "display_demo_3",
        "advertiser": "Canada Post",
        "title": "Skip the lobby. Pick up parcels on your walk.",
        "clickUrl": "https://www.canadapost-postescanada.ca/",
        "imageKey": "local/ads/display/ad_demo_3.jpg",
        "imageAspect": 0.72,
        "active": True,
        "slot": "storylines_list",
        "slots": ["storylines_list"],
    },
]


def main() -> None:
    _require_local(URI)
    client = MongoClient(URI, serverSelectionTimeoutMS=5000)
    db = client[DB]
    for ad in ADS:
        db.display_ads.update_one({"adId": ad["adId"]}, {"$set": ad}, upsert=True)
    print(f"Seeded {len(ADS)} display ads into {DB}.display_ads")


if __name__ == "__main__":
    main()
