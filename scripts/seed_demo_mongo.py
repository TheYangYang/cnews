#!/usr/bin/env python3
"""Seed MongoDB with a scrollable wall of sample stories (no Ollama required).

Covers: API wwwroot/media/covers/story_demo_{n}.jpg (real photos, no baked text).
Audio:  Kokoro → Opus + m4a (scripts/generate_kokoro_briefs.py).
        Seed serves m4a for iOS Expo; audioOpusKey keeps the prod Opus key.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from pymongo import MongoClient

URI = "mongodb://127.0.0.1:27017"
DB = "cnews"
PUBLIC = "http://10.0.0.100:5080"

# title, summary, outlet, topic, place, aspect, sourceUrl
STORIES = [
    ("Prairie storm knocks out power across southern Manitoba", "High winds cut power to tens of thousands of homes. Crews are restoring lines overnight while schools delay openings in Winnipeg and Brandon.", "CBC", "Local", "Manitoba", 0.68, "https://www.cbc.ca/news"),
    ("Manitoba storm leaves wide outages, travel disrupted", "Global reports highway closures and delayed flights as the same weather system moves east. Utilities say full restoration may take days in rural areas.", "Global", "Local", "Manitoba", 0.72, "https://globalnews.ca/"),
    ("Bank of Canada holds rate as inflation cools", "Officials kept the policy rate unchanged, citing slower price growth and a softer labour market. Markets expect cuts later this year if trends continue.", "Globe and Mail", "Business", "Canada", 0.7, "https://www.theglobeandmail.com/"),
    ("Canada and allies push new Arctic research pact", "Ottawa joined partners on shared ice mapping and climate monitoring. The deal aims to expand science access while keeping shipping routes safer.", "CBC", "Canada", "Canada", 0.65, "https://www.cbc.ca/news/canada"),
    ("Toronto transit plan adds late-night weekend trains", "The city will trial extended subway hours on Fridays and Saturdays. Officials say the change targets nightlife workers and event crowds downtown.", "Toronto Star", "Local", "Toronto", 0.7, "https://www.thestar.com/"),
    ("Health agencies urge early flu shots this fall", "Doctors expect an earlier peak and want high-risk groups vaccinated first. Clinics are expanding evening appointments in several provinces.", "CBC", "Health", "Canada", 0.66, "https://www.cbc.ca/news/health"),
    ("Ottawa unveils housing incentives for mid-size cities", "Federal officials outlined rental build credits outside the largest metros, asking provinces to align zoning within eighteen months.", "CBC", "Canada", "Ottawa", 0.74, "https://www.cbc.ca/news/politics"),
    ("Wildfire smoke prompts air-quality alerts on the Prairies", "Health officials recommend limiting outdoor activity for sensitive groups as plumes drift east from Alberta.", "CTV", "Canada", "Calgary", 0.8, "https://www.ctvnews.ca/"),
    ("Vancouver port talks resume with federal mediator", "Both sides remain far apart on shift scheduling but agreed to daily sessions this week to keep cargo moving.", "Global", "Business", "Vancouver", 0.69, "https://globalnews.ca/news/"),
    ("Quebec expands nurse practitioner hospital roles", "A new bill would let NPs admit patients in select rural hospitals, pending college approval this winter.", "La Presse", "Health", "Quebec City", 0.71, "https://www.lapresse.ca/"),
    ("Halifax startup raises seed for tidal energy sensors", "The company plans Bay of Fundy pilots with utility partners next spring after closing a seed round.", "AllNovaScotia", "Business", "Halifax", 0.67, "https://www.allnovascotia.com/"),
    ("Montreal metro signal upgrades shorten weekend closures", "STM says two lines will see fewer full-day shutdowns once new interlocking software finishes testing.", "CBC", "Local", "Montreal", 0.73, "https://www.cbc.ca/news/canada/montreal"),
    ("Alberta budget puts more into wildfire crews", "The province adds seasonal firefighters and equipment after last summer’s record burn season.", "Edmonton Journal", "Canada", "Alberta", 0.76, "https://edmontonjournal.com/"),
    ("Canada’s tech hiring cools as AI labs consolidate", "Recruiters report fewer junior roles while demand for applied machine-learning talent stays firm.", "Financial Post", "Business", "Toronto", 0.64, "https://financialpost.com/"),
    ("Atlantic ferry schedules expand for summer tourism", "Operators add sailings between Nova Scotia and Newfoundland to ease peak weekend waits.", "CBC", "Canada", "Atlantic", 0.78, "https://www.cbc.ca/news/canada/nova-scotia"),
    ("Ontario schools expand before-and-after care seats", "The province funds new spaces in forty boards, prioritizing communities with long wait lists.", "Toronto Star", "Local", "Ontario", 0.7, "https://www.thestar.com/news"),
    ("Researchers map faster glacier melt in Yukon", "Satellite data shows summer ice loss exceeding five-year model averages, raising flood risk downstream.", "CBC", "Canada", "Yukon", 0.62, "https://www.cbc.ca/news/canada/north"),
    ("Grocery chains test smaller urban discount formats", "Pilot stores focus on staples and private label as shoppers push back on food inflation.", "Globe and Mail", "Business", "Canada", 0.75, "https://www.theglobeandmail.com/business/"),
    ("Canada Soccer names new women’s coaching staff", "The federation confirms a multi-year deal ahead of the next World Cup qualifying cycle.", "TSN", "Canada", "Canada", 0.68, "https://www.tsn.ca/"),
    ("BC Hydro warns of peak-hour pricing this winter", "Customers can shift laundry and EV charging to off-peak windows to avoid higher rates.", "Global", "Local", "Vancouver", 0.72, "https://globalnews.ca/news/british-columbia/"),
    ("Federal privacy bill advances through committee", "MPs tightened rules on children’s data and AI training sets after weeks of hearings.", "CBC", "Politics", "Ottawa", 0.7, "https://www.cbc.ca/news/politics"),
    ("Saskatoon hospital adds overnight MRI capacity", "Health region says the change should cut diagnostic waits for rural referrals by weeks.", "CBC", "Health", "Saskatoon", 0.69, "https://www.cbc.ca/news/canada/saskatoon"),
    ("Canada Post trials neighbourhood parcel lockers", "The pilot aims to cut failed doorstep deliveries in dense condo areas of Toronto and Vancouver.", "Globe and Mail", "Business", "Canada", 0.71, "https://www.theglobeandmail.com/business/"),
    ("Indigenous-led conservation area expands in North", "A new agreement protects caribou habitat while keeping community hunting rights intact.", "CBC", "Canada", "NWT", 0.66, "https://www.cbc.ca/news/indigenous"),
]


def main() -> None:
    client = MongoClient(URI, serverSelectionTimeoutMS=5000)
    db = client[DB]
    now = datetime.now(timezone.utc)

    # Replace wall content so pagination is clean.
    db.stories.delete_many({"storyId": {"$regex": r"^story_demo_"}})

    docs = []
    for idx, (title, summary, outlet, topic, place, aspect, source_url) in enumerate(
        STORIES, start=1
    ):
        sid = f"story_demo_{idx}"
        # First two share a coverage cluster / storyline.
        cluster = "cluster_demo_a" if idx in (1, 2) else None
        thread = "thread_demo_1" if idx in (1, 2) else None
        audio_n = ((idx - 1) % 6) + 1  # reuse 6 Kokoro briefs until more are generated
        docs.append(
            {
                "storyId": sid,
                "clusterId": cluster,
                "threadId": thread,
                "title": title,
                "summary": summary,
                "summaryWords": len(summary.split()),
                "summaryEngine": "seed",
                "imageUrl": f"{PUBLIC}/media/covers/{sid}.jpg",
                "imageAspect": aspect,
                "outlet": outlet,
                "topic": topic,
                "place": place,
                "sourceUrl": source_url,
                "publishedAt": now - timedelta(hours=idx),
                "ingestedAt": now - timedelta(hours=idx),
                # Kokoro Opus is the production artifact; m4a twin is for iOS Expo playback.
                "audioStatus": "ready",
                "audioKey": f"local/story_demo_{audio_n}.m4a",
                "audioOpusKey": f"local/story_demo_{audio_n}.opus",
                "audioContentType": "audio/mp4",
                "audioDurationMs": 14000,
                "listenReady": True,
                "textReady": True,
            }
        )

    for story in docs:
        db.stories.update_one({"storyId": story["storyId"]}, {"$set": story}, upsert=True)

    db.compares.update_one(
        {"clusterId": "cluster_demo_a"},
        {
            "$set": {
                "clusterId": "cluster_demo_a",
                "title": "Manitoba storm and power outages",
                "topics": ["Local", "Canada"],
                "updatedAt": now,
                "outlets": [
                    {
                        "storyId": "story_demo_1",
                        "outlet": "CBC",
                        "framing": "Led with household outages and school delays.",
                        "summary": docs[0]["summary"],
                        "audioStatus": "ready",
                        "audioKey": "local/story_demo_1.m4a",
                        "sourceUrl": "https://www.cbc.ca/",
                        "imageUrl": docs[0]["imageUrl"],
                    },
                    {
                        "storyId": "story_demo_2",
                        "outlet": "Global",
                        "framing": "Led with highway closures and travel disruption.",
                        "summary": docs[1]["summary"],
                        "audioStatus": "ready",
                        "audioKey": "local/story_demo_2.m4a",
                        "sourceUrl": "https://globalnews.ca/",
                        "imageUrl": docs[1]["imageUrl"],
                    },
                ],
            }
        },
        upsert=True,
    )

    def upd(doc_idx: int, hours_ago: float) -> dict:
        d = docs[doc_idx]
        audio_n = ((doc_idx) % 6) + 1
        return {
            "storyId": d["storyId"],
            "at": now - timedelta(hours=hours_ago),
            "outlet": d["outlet"],
            "summary": d["summary"],
            "title": d["title"],
            "audioStatus": "ready",
            "audioKey": f"local/story_demo_{audio_n}.m4a",
            "sourceUrl": d["sourceUrl"],
            "imageUrl": d["imageUrl"],
        }

    threads = [
        {
            "threadId": "thread_demo_1",
            "title": "Manitoba storm recovery",
            "status": "open",
            "topic": "Local",
            "place": "Manitoba",
            "openedAt": now - timedelta(hours=6),
            "closedAt": None,
            "updatedAt": now - timedelta(hours=1),
            "updates": [upd(1, 3), upd(0, 1)],
        },
        {
            "threadId": "thread_demo_2",
            "title": "Bank of Canada rate path",
            "status": "open",
            "topic": "Business",
            "place": "Canada",
            "openedAt": now - timedelta(hours=20),
            "closedAt": None,
            "updatedAt": now - timedelta(hours=3),
            "updates": [upd(2, 8), upd(13, 3)],
        },
        {
            "threadId": "thread_demo_3",
            "title": "West Coast port talks",
            "status": "open",
            "topic": "Business",
            "place": "Vancouver",
            "openedAt": now - timedelta(hours=30),
            "closedAt": None,
            "updatedAt": now - timedelta(hours=4),
            "updates": [upd(8, 12), upd(19, 4)],
        },
        {
            "threadId": "thread_demo_4",
            "title": "Prairie wildfire smoke season",
            "status": "open",
            "topic": "Canada",
            "place": "Alberta",
            "openedAt": now - timedelta(hours=48),
            "closedAt": None,
            "updatedAt": now - timedelta(hours=5),
            "updates": [upd(7, 20), upd(12, 5)],
        },
        {
            "threadId": "thread_demo_5",
            "title": "Federal privacy bill hearings",
            "status": "closed",
            "topic": "Politics",
            "place": "Ottawa",
            "openedAt": now - timedelta(days=5),
            "closedAt": now - timedelta(hours=10),
            "updatedAt": now - timedelta(hours=10),
            "updates": [upd(20, 30), upd(6, 10)],
        },
    ]

    db.threads.delete_many({"threadId": {"$regex": r"^thread_demo_"}})
    for thread in threads:
        db.threads.update_one({"threadId": thread["threadId"]}, {"$set": thread}, upsert=True)

    print(
        f"Seeded {len(docs)} stories + {len(threads)} storylines into {DB} "
        "(covers + spoken audio ready)"
    )


if __name__ == "__main__":
    main()
