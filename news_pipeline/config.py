"""Feed registry defaults, Redis, and model endpoints."""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "news.db"
AUDIO_DIR = DATA_DIR / "audio"

# name, url, outlet, category, place, poll seconds.
# Category is the topic chip. Place is the province or city chip. Several feeds can share both,
# which is what lets different outlets show up in the same comparison.
_CATALOG = [
    ("CBC Top Stories", "https://rss.cbc.ca/lineup/topstories.xml", "CBC", "Top", "Canada", 120),
    ("CBC Canada", "https://rss.cbc.ca/lineup/canada.xml", "CBC", "Canada", "Canada", 120),
    ("CBC World", "https://rss.cbc.ca/lineup/world.xml", "CBC", "World", "Canada", 180),
    ("CBC Politics", "https://rss.cbc.ca/lineup/politics.xml", "CBC", "Politics", "Canada", 120),
    ("CBC Business", "https://rss.cbc.ca/lineup/business.xml", "CBC", "Business", "Canada", 180),
    ("CBC Health", "https://rss.cbc.ca/lineup/health.xml", "CBC", "Health", "Canada", 300),
    ("CBC Arts", "https://rss.cbc.ca/lineup/arts.xml", "CBC", "Arts", "Canada", 300),
    ("CBC Technology", "https://rss.cbc.ca/lineup/technology.xml", "CBC", "Technology", "Canada", 300),
    ("CBC Sports", "https://rss.cbc.ca/lineup/sports.xml", "CBC", "Sports", "Canada", 180),
    ("CBC British Columbia", "https://rss.cbc.ca/lineup/canada-britishcolumbia.xml", "CBC", "Local", "British Columbia", 600),
    ("CBC Calgary", "https://rss.cbc.ca/lineup/canada-calgary.xml", "CBC", "Local", "Calgary", 600),
    ("CBC Edmonton", "https://rss.cbc.ca/lineup/canada-edmonton.xml", "CBC", "Local", "Edmonton", 600),
    ("CBC Saskatchewan", "https://rss.cbc.ca/lineup/canada-saskatchewan.xml", "CBC", "Local", "Saskatchewan", 600),
    ("CBC Manitoba", "https://rss.cbc.ca/lineup/canada-manitoba.xml", "CBC", "Local", "Manitoba", 600),
    ("CBC Toronto", "https://rss.cbc.ca/lineup/canada-toronto.xml", "CBC", "Local", "Toronto", 600),
    ("CBC Ottawa", "https://rss.cbc.ca/lineup/canada-ottawa.xml", "CBC", "Local", "Ottawa", 600),
    ("CBC Montreal", "https://rss.cbc.ca/lineup/canada-montreal.xml", "CBC", "Local", "Montreal", 600),
    ("CBC Kitchener-Waterloo", "https://rss.cbc.ca/lineup/canada-kitchenerwaterloo.xml", "CBC", "Local", "Kitchener", 600),
    ("CBC London", "https://rss.cbc.ca/lineup/canada-london.xml", "CBC", "Local", "London", 600),
    ("CBC Windsor", "https://rss.cbc.ca/lineup/canada-windsor.xml", "CBC", "Local", "Windsor", 600),
    ("CBC Sudbury", "https://rss.cbc.ca/lineup/canada-sudbury.xml", "CBC", "Local", "Sudbury", 600),
    ("CBC Thunder Bay", "https://rss.cbc.ca/lineup/canada-thunderbay.xml", "CBC", "Local", "Thunder Bay", 600),
    ("CBC Saskatoon", "https://rss.cbc.ca/lineup/canada-saskatoon.xml", "CBC", "Local", "Saskatoon", 600),
    ("CBC Kamloops", "https://rss.cbc.ca/lineup/canada-kamloops.xml", "CBC", "Local", "Kamloops", 600),
    ("CBC New Brunswick", "https://rss.cbc.ca/lineup/canada-newbrunswick.xml", "CBC", "Local", "New Brunswick", 600),
    ("CBC Nova Scotia", "https://rss.cbc.ca/lineup/canada-novascotia.xml", "CBC", "Local", "Nova Scotia", 600),
    ("CBC Prince Edward Island", "https://rss.cbc.ca/lineup/canada-pei.xml", "CBC", "Local", "Prince Edward Island", 600),
    ("CBC Newfoundland and Labrador", "https://rss.cbc.ca/lineup/canada-newfoundland.xml", "CBC", "Local", "Newfoundland and Labrador", 600),
    ("CBC North", "https://rss.cbc.ca/lineup/canada-north.xml", "CBC", "Local", "North", 600),
    ("Global Top Stories", "https://globalnews.ca/feed/", "Global", "Top", "Canada", 180),
    ("Global Canada", "https://globalnews.ca/canada/feed/", "Global", "Canada", "Canada", 180),
    ("Global World", "https://globalnews.ca/world/feed/", "Global", "World", "Canada", 180),
    ("Global Politics", "https://globalnews.ca/politics/feed/", "Global", "Politics", "Canada", 180),
    ("Global Business", "https://globalnews.ca/money/feed/", "Global", "Business", "Canada", 300),
    ("Global Health", "https://globalnews.ca/health/feed/", "Global", "Health", "Canada", 300),
    ("Global Arts", "https://globalnews.ca/entertainment/feed/", "Global", "Arts", "Canada", 300),
    ("Global Technology", "https://globalnews.ca/tech/feed/", "Global", "Technology", "Canada", 300),
    ("Global Sports", "https://globalnews.ca/sports/feed/", "Global", "Sports", "Canada", 180),
    ("Global British Columbia", "https://globalnews.ca/bc/feed/", "Global", "Local", "British Columbia", 600),
    ("Global Calgary", "https://globalnews.ca/calgary/feed/", "Global", "Local", "Calgary", 600),
    ("Global Edmonton", "https://globalnews.ca/edmonton/feed/", "Global", "Local", "Edmonton", 600),
    ("Global Lethbridge", "https://globalnews.ca/lethbridge/feed/", "Global", "Local", "Lethbridge", 600),
    ("Global Okanagan", "https://globalnews.ca/okanagan/feed/", "Global", "Local", "Kelowna", 600),
    ("Global Regina", "https://globalnews.ca/regina/feed/", "Global", "Local", "Regina", 600),
    ("Global Saskatoon", "https://globalnews.ca/saskatoon/feed/", "Global", "Local", "Saskatoon", 600),
    ("Global Winnipeg", "https://globalnews.ca/winnipeg/feed/", "Global", "Local", "Winnipeg", 600),
    ("Global Toronto", "https://globalnews.ca/toronto/feed/", "Global", "Local", "Toronto", 600),
    ("Global Ottawa", "https://globalnews.ca/ottawa/feed/", "Global", "Local", "Ottawa", 600),
    ("Global Hamilton", "https://globalnews.ca/hamilton/feed/", "Global", "Local", "Hamilton", 600),
    ("Global London", "https://globalnews.ca/london/feed/", "Global", "Local", "London", 600),
    ("Global Kingston", "https://globalnews.ca/kingston/feed/", "Global", "Local", "Kingston", 600),
    ("Global Barrie", "https://globalnews.ca/barrie/feed/", "Global", "Local", "Barrie", 600),
    ("Global Peterborough", "https://globalnews.ca/peterborough/feed/", "Global", "Local", "Peterborough", 600),
    ("Global Montreal", "https://globalnews.ca/montreal/feed/", "Global", "Local", "Montreal", 600),
    ("Global Halifax", "https://globalnews.ca/halifax/feed/", "Global", "Local", "Halifax", 600),
    ("Global New Brunswick", "https://globalnews.ca/new-brunswick/feed/", "Global", "Local", "New Brunswick", 600),
    ("Toronto Star", "https://www.thestar.com/search/?f=rss&t=article&c=news*", "Toronto Star", "Canada", "Canada", 180),
    ("Globe and Mail Canada", "https://www.theglobeandmail.com/arc/outboundfeeds/rss/category/canada/?outputType=xml", "Globe and Mail", "Canada", "Canada", 180),
    ("Globe and Mail World", "https://www.theglobeandmail.com/arc/outboundfeeds/rss/category/world/?outputType=xml", "Globe and Mail", "World", "Canada", 180),
    ("Globe and Mail Politics", "https://www.theglobeandmail.com/arc/outboundfeeds/rss/category/politics/?outputType=xml", "Globe and Mail", "Politics", "Canada", 180),
    ("Globe and Mail Business", "https://www.theglobeandmail.com/arc/outboundfeeds/rss/category/business/?outputType=xml", "Globe and Mail", "Business", "Canada", 300),
    ("National Post", "https://nationalpost.com/feed/", "National Post", "Canada", "Canada", 180),
    ("Financial Post", "https://financialpost.com/feed/", "Financial Post", "Business", "Canada", 300),
    ("The Canadian Press", "https://www.thecanadianpressnews.ca/search/?f=rss", "The Canadian Press", "Canada", "Canada", 180),
    ("APTN", "https://www.aptnnews.ca/feed/", "APTN", "Canada", "Canada", 300),
    ("IndigiNews", "https://indiginews.com/feed/", "IndigiNews", "Canada", "Canada", 600),
    ("The Narwhal", "https://thenarwhal.ca/feed/", "The Narwhal", "Canada", "Canada", 600),
    ("iPolitics", "https://www.ipolitics.ca/feed/", "iPolitics", "Politics", "Canada", 300),
    ("Radio-Canada", "https://ici.radio-canada.ca/rss/4159", "Radio-Canada", "Canada", "Canada", 180),
    ("La Presse", "https://www.lapresse.ca/actualites/rss", "La Presse", "Canada", "Quebec", 180),
    ("Le Devoir", "https://www.ledevoir.com/rss/manchettes.xml", "Le Devoir", "Canada", "Quebec", 180),
    ("L'actualite", "https://lactualite.com/feed/", "L'actualite", "Canada", "Quebec", 300),
    ("TVA Nouvelles", "https://www.tvanouvelles.ca/rss.xml", "TVA", "Canada", "Quebec", 180),
    ("CityNews Vancouver", "https://vancouver.citynews.ca/feed/", "CityNews", "Local", "Vancouver", 600),
    ("CityNews Calgary", "https://calgary.citynews.ca/feed/", "CityNews", "Local", "Calgary", 600),
    ("CityNews Edmonton", "https://edmonton.citynews.ca/feed/", "CityNews", "Local", "Edmonton", 600),
    ("CityNews Winnipeg", "https://winnipeg.citynews.ca/feed/", "CityNews", "Local", "Winnipeg", 600),
    ("CityNews Toronto", "https://toronto.citynews.ca/feed/", "CityNews", "Local", "Toronto", 600),
    ("CityNews Ottawa", "https://ottawa.citynews.ca/feed/", "CityNews", "Local", "Ottawa", 600),
    ("CityNews Kitchener", "https://kitchener.citynews.ca/feed/", "CityNews", "Local", "Kitchener", 600),
    ("CityNews Montreal", "https://montreal.citynews.ca/feed/", "CityNews", "Local", "Montreal", 600),
    ("CityNews Halifax", "https://halifax.citynews.ca/feed/", "CityNews", "Local", "Halifax", 600),
    ("Vancouver Sun", "https://vancouversun.com/feed/", "Vancouver Sun", "Local", "Vancouver", 600),
    ("The Province", "https://theprovince.com/feed/", "The Province", "Local", "Vancouver", 600),
    ("The Tyee", "https://thetyee.ca/rss2.xml", "The Tyee", "Local", "British Columbia", 600),
    ("CHEK Victoria", "https://www.cheknews.ca/feed/", "CHEK", "Local", "Victoria", 600),
    ("Prince George Citizen", "https://www.princegeorgecitizen.com/rss", "Prince George Citizen", "Local", "Prince George", 600),
    ("Calgary Herald", "https://calgaryherald.com/feed/", "Calgary Herald", "Local", "Calgary", 600),
    ("Calgary Sun", "https://calgarysun.com/feed/", "Calgary Sun", "Local", "Calgary", 600),
    ("Edmonton Journal", "https://edmontonjournal.com/feed/", "Edmonton Journal", "Local", "Edmonton", 600),
    ("Edmonton Sun", "https://edmontonsun.com/feed/", "Edmonton Sun", "Local", "Edmonton", 600),
    ("Winnipeg Free Press", "https://www.winnipegfreepress.com/rss", "Winnipeg Free Press", "Local", "Winnipeg", 600),
    ("Brandon Sun", "https://www.brandonsun.com/rss", "Brandon Sun", "Local", "Brandon", 600),
    ("Toronto Sun", "https://torontosun.com/feed/", "Toronto Sun", "Local", "Toronto", 600),
    ("Ottawa Citizen", "https://ottawacitizen.com/feed/", "Ottawa Citizen", "Local", "Ottawa", 600),
    ("Ottawa Sun", "https://ottawasun.com/feed/", "Ottawa Sun", "Local", "Ottawa", 600),
    ("SooToday", "https://www.sootoday.com/rss", "SooToday", "Local", "Sault Ste. Marie", 600),
    ("Journal de Montreal", "https://www.journaldemontreal.com/rss.xml", "Journal de Montreal", "Local", "Montreal", 600),
    ("Journal de Quebec", "https://www.journaldequebec.com/rss.xml", "Journal de Quebec", "Local", "Quebec City", 600),
    ("Acadie Nouvelle", "https://www.acadienouvelle.com/feed/", "Acadie Nouvelle", "Local", "New Brunswick", 600),
    ("Telegraph-Journal", "https://tj.news/feed", "Telegraph-Journal", "Local", "New Brunswick", 600),
    ("Halifax Examiner", "https://www.halifaxexaminer.ca/feed/", "Halifax Examiner", "Local", "Halifax", 600),
    ("SaltWire", "https://www.saltwire.com/rss", "SaltWire", "Local", "Atlantic", 600),
    ("Yukon News", "https://www.yukon-news.com/feed/", "Yukon News", "Local", "Whitehorse", 600),
    ("Cabin Radio", "https://cabinradio.ca/feed/", "Cabin Radio", "Local", "Yellowknife", 600),
    ("Northern News Services", "https://www.nnsl.com/feed/", "Northern News Services", "Local", "Yellowknife", 600),
    ("Nunatsiaq News", "https://nunatsiaq.com/feed/", "Nunatsiaq News", "Local", "Iqaluit", 600),
]

FEEDS = [
    {
        "name": name,
        "url": url,
        "outlet": outlet,
        "category": category,
        "place": place,
        "poll_interval_seconds": seconds,
    }
    for name, url, outlet, category, place, seconds in _CATALOG
]

TOPIC_ORDER = [
    "Top",
    "Canada",
    "Local",
    "World",
    "Politics",
    "Business",
    "Health",
    "Arts",
    "Technology",
    "Sports",
]
PLACE_ORDER = [
    "Canada",
    "British Columbia",
    "Vancouver",
    "Victoria",
    "Kelowna",
    "Kamloops",
    "Prince George",
    "Alberta",
    "Calgary",
    "Edmonton",
    "Lethbridge",
    "Saskatchewan",
    "Regina",
    "Saskatoon",
    "Manitoba",
    "Winnipeg",
    "Brandon",
    "Ontario",
    "Toronto",
    "Ottawa",
    "Hamilton",
    "London",
    "Kitchener",
    "Windsor",
    "Barrie",
    "Kingston",
    "Peterborough",
    "Sudbury",
    "Sault Ste. Marie",
    "Thunder Bay",
    "Quebec",
    "Montreal",
    "Quebec City",
    "New Brunswick",
    "Nova Scotia",
    "Halifax",
    "Atlantic",
    "Prince Edward Island",
    "Newfoundland and Labrador",
    "North",
    "Whitehorse",
    "Yellowknife",
    "Iqaluit",
]

REDIS_URL = os.environ.get("REDIS_URL", "redis://127.0.0.1:6379/0")
STREAM_ARTICLES = "news:articles"
STREAM_SUMMARIES = "news:summaries"
GROUP_AI = "ai-workers"
GROUP_TTS = "tts-workers"
SEEN_TTL_SECONDS = 7 * 24 * 60 * 60

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
# Diagram calls for Llama-3 8B. This machine has the Llama 3.1 8B tag.
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.1:8b")
SUMMARY_WORDS = 50

KOKORO_VOICE = os.environ.get("KOKORO_VOICE", "af_heart")
KOKORO_SAMPLE_RATE = 24_000

UI_HOST = "127.0.0.1"
UI_PORT = 8765

# Keep each poll short so summaries show up while the rest of the feed waits.
# With dozens of feeds, two new stories per poll keeps the local model from falling behind.
MAX_NEW_ARTICLES_PER_POLL = 2
ARTICLE_FETCH_CONCURRENCY = 3
PROMPT_CHAR_LIMIT = 4500

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
)
