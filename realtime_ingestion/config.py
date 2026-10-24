"""Feed registry defaults, Redis, and model endpoints."""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load_dotenv(path: Path) -> None:
    """Read KEY=VALUE lines into os.environ. Real environment variables win."""
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.removeprefix("export ").strip()
        value = value.strip().strip("\"'")
        os.environ.setdefault(key, value)


_load_dotenv(Path(os.environ.get("CNEWS_ENV_FILE", ROOT / ".env")))


def _flag(name: str, default: str) -> bool:
    return os.environ.get(name, default).lower() in {"1", "true", "yes"}


DATA_DIR = Path(os.environ.get("CNEWS_DATA_DIR", ROOT / "data"))
DB_PATH = DATA_DIR / "news.db"
AUDIO_DIR = DATA_DIR / "audio"

# name, url, outlet, category, place, poll seconds.
# English-only: Kokoro has no French voice. Category is the topic chip; place is city/province.
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
    ("Global Guelph", "https://globalnews.ca/guelph/feed/", "Global", "Local", "Guelph", 600),
    ("Global Durham", "https://globalnews.ca/durham/feed/", "Global", "Local", "Oshawa", 600),
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
    ("Telegraph-Journal", "https://tj.news/feed", "Telegraph-Journal", "Local", "New Brunswick", 600),
    ("Halifax Examiner", "https://www.halifaxexaminer.ca/feed/", "Halifax Examiner", "Local", "Halifax", 600),
    ("SaltWire", "https://www.saltwire.com/rss", "SaltWire", "Local", "Atlantic", 600),
    ("Yukon News", "https://www.yukon-news.com/feed/", "Yukon News", "Local", "Whitehorse", 600),
    ("Cabin Radio", "https://cabinradio.ca/feed/", "Cabin Radio", "Local", "Yellowknife", 600),
    ("Northern News Services", "https://www.nnsl.com/feed/", "Northern News Services", "Local", "Yellowknife", 600),
    ("Nunatsiaq News", "https://nunatsiaq.com/feed/", "Nunatsiaq News", "Local", "Iqaluit", 600),
    ("Toronto Star GTA", "https://www.thestar.com/search/?f=rss&t=article&c=news/gta", "Toronto Star", "Local", "Toronto", 600),
    ("Hamilton Spectator", "https://www.thespec.com/search/?f=rss&t=article&c=news", "Hamilton Spectator", "Local", "Hamilton", 600),
    ("Waterloo Region Record", "https://www.therecord.com/search/?f=rss&t=article&c=news", "Waterloo Region Record", "Local", "Kitchener", 600),
    ("St. Catharines Standard", "https://www.stcatharinesstandard.ca/search/?f=rss&t=article&c=news", "St. Catharines Standard", "Local", "St. Catharines", 600),
    ("Niagara Falls Review", "https://www.niagarafallsreview.ca/search/?f=rss&t=article&c=news", "Niagara Falls Review", "Local", "Niagara", 600),
    ("Peterborough Examiner", "https://www.thepeterboroughexaminer.com/search/?f=rss&t=article&c=news", "Peterborough Examiner", "Local", "Peterborough", 600),
    ("Times Colonist", "https://www.timescolonist.com/rss", "Times Colonist", "Local", "Victoria", 600),
    ("Nanaimo Bulletin", "https://www.nanaimobulletin.com/rss", "Nanaimo Bulletin", "Local", "Nanaimo", 600),
    ("Alberni Valley News", "https://www.albernivalleynews.com/rss", "Alberni Valley News", "Local", "Port Alberni", 600),
    ("PQB News", "https://www.pqbnews.com/rss", "PQB News", "Local", "Parksville", 600),
    ("Campbell River Mirror", "https://www.campbellrivermirror.com/rss", "Campbell River Mirror", "Local", "Campbell River", 600),
    ("Cowichan Valley Citizen", "https://www.cowichanvalleycitizen.com/rss", "Cowichan Valley Citizen", "Local", "Cowichan", 600),
    ("Langley Advance Times", "https://www.langleyadvancetimes.com/rss", "Langley Advance Times", "Local", "Langley", 600),
    ("Delta Optimist", "https://www.delta-optimist.com/rss", "Delta Optimist", "Local", "Delta", 600),
    ("Maple Ridge News", "https://www.mapleridgenews.com/rss", "Maple Ridge News", "Local", "Maple Ridge", 600),
    ("Kelowna Capital News", "https://www.kelownacapnews.com/rss", "Kelowna Capital News", "Local", "Kelowna", 600),
    ("Vernon Morning Star", "https://www.vernonmorningstar.com/rss", "Vernon Morning Star", "Local", "Vernon", 600),
    ("Penticton Western News", "https://www.pentictonwesternnews.com/rss", "Penticton Western News", "Local", "Penticton", 600),
    ("Nelson Star", "https://www.nelsonstar.com/rss", "Nelson Star", "Local", "Nelson", 600),
    ("Cranbrook Townsman", "https://www.cranbrooktownsman.com/rss", "Cranbrook Townsman", "Local", "Cranbrook", 600),
    ("Terrace Standard", "https://www.terracestandard.com/rss", "Terrace Standard", "Local", "Terrace", 600),
    ("Quesnel Observer", "https://www.quesnelobserver.com/rss", "Quesnel Observer", "Local", "Quesnel", 600),
    ("Red Deer Advocate", "https://www.reddeeradvocate.com/rss", "Red Deer Advocate", "Local", "Red Deer", 600),
    ("Medicine Hat News", "https://medicinehatnews.com/feed/", "Medicine Hat News", "Local", "Medicine Hat", 600),
    ("Lethbridge Herald", "https://lethbridgeherald.com/feed/", "Lethbridge Herald", "Local", "Lethbridge", 600),
    ("Airdrie City View", "https://www.airdriecityview.com/rss", "Airdrie City View", "Local", "Airdrie", 600),
    ("St. Albert Gazette", "https://www.stalbertgazette.com/rss", "St. Albert Gazette", "Local", "St. Albert", 600),
    ("GuelphToday", "https://www.guelphtoday.com/rss", "GuelphToday", "Local", "Guelph", 600),
    ("CambridgeToday", "https://www.cambridgetoday.ca/rss", "CambridgeToday", "Local", "Cambridge", 600),
    ("BarrieToday", "https://www.barrietoday.com/rss", "BarrieToday", "Local", "Barrie", 600),
    ("OrilliaMatters", "https://www.orilliamatters.com/rss", "OrilliaMatters", "Local", "Orillia", 600),
    ("NewmarketToday", "https://www.newmarkettoday.ca/rss", "NewmarketToday", "Local", "Newmarket", 600),
    ("Kingstonist", "https://www.kingstonist.com/rss", "Kingstonist", "Local", "Kingston", 600),
    ("Sudbury.com", "https://www.sudbury.com/rss", "Sudbury.com", "Local", "Sudbury", 600),
    ("TimminsToday", "https://www.timminstoday.com/rss", "TimminsToday", "Local", "Timmins", 600),
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
    "Nanaimo",
    "Langley",
    "Delta",
    "Maple Ridge",
    "Kelowna",
    "Vernon",
    "Penticton",
    "Kamloops",
    "Prince George",
    "Parksville",
    "Port Alberni",
    "Campbell River",
    "Cowichan",
    "Nelson",
    "Cranbrook",
    "Terrace",
    "Quesnel",
    "Alberta",
    "Calgary",
    "Edmonton",
    "Red Deer",
    "Lethbridge",
    "Medicine Hat",
    "Airdrie",
    "St. Albert",
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
    "Cambridge",
    "Guelph",
    "Oshawa",
    "Newmarket",
    "Windsor",
    "Barrie",
    "Orillia",
    "Kingston",
    "Peterborough",
    "Niagara",
    "St. Catharines",
    "Sudbury",
    "Timmins",
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

# Streams are trimmed to roughly this many entries so Redis memory stays flat.
STREAM_MAXLEN = int(os.environ.get("STREAM_MAXLEN", "5000"))

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
# Diagram calls for Llama-3 8B. This machine has the Llama 3.1 8B tag.
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.1:8b")
# Every call must send the same num_ctx, or Ollama reloads the model between calls.
# 3072 fits a clipped article prompt and keeps the KV cache small on a 6 GB card.
OLLAMA_NUM_CTX = int(os.environ.get("OLLAMA_NUM_CTX", "3072"))
OLLAMA_KEEP_ALIVE = os.environ.get("OLLAMA_KEEP_ALIVE", "30m")
OLLAMA_TIMEOUT_SECONDS = float(os.environ.get("OLLAMA_TIMEOUT_SECONDS", "180"))
SUMMARY_WORDS = 50
# Storyline prompts list open threads; cap them so the prompt stays inside num_ctx.
THREAD_PROMPT_MAX_OPEN = int(os.environ.get("THREAD_PROMPT_MAX_OPEN", "30"))
# Only review recent briefs for storylines; older backlog is not worth GPU time.
THREAD_REVIEW_WINDOW_HOURS = int(os.environ.get("THREAD_REVIEW_WINDOW_HOURS", "48"))

KOKORO_VOICE = os.environ.get("KOKORO_VOICE", "af_heart")
KOKORO_SAMPLE_RATE = 24_000
TTS_ENABLED = _flag("TTS_ENABLED", "true")
# auto picks cuda when torch sees a GPU, else cpu.
TTS_DEVICE = os.environ.get("TTS_DEVICE", "auto").lower()
OPUS_BITRATE = os.environ.get("OPUS_BITRATE", "32k")

# GPU scheduling (see docs/real-time-ingestion/pipeline.md, "GPU scheduling").
GPU_GATE_ENABLED = _flag("GPU_GATE_ENABLED", "true")
# When Ollama and Kokoro share one small card (GTX 1060), unload the LLM before a
# speech turn so Kokoro runs at full speed, and park Kokoro on CPU after the turn.
GPU_SWAP_MODELS = _flag("GPU_SWAP_MODELS", "true")
# Speech starts only after the LLM has been quiet this long (avoids swapping mid-burst).
TTS_IDLE_GRACE_SECONDS = float(os.environ.get("TTS_IDLE_GRACE_SECONDS", "4"))
# If a brief has waited this long for speech, take a speech turn even during a burst.
TTS_MAX_LAG_SECONDS = float(os.environ.get("TTS_MAX_LAG_SECONDS", "240"))
# A speech turn speaks at least this many briefs before yielding to new LLM work
# (amortizes the model swap); a forced turn speaks up to TTS_TURN_MAX.
TTS_TURN_MIN = int(os.environ.get("TTS_TURN_MIN", "4"))
TTS_TURN_MAX = int(os.environ.get("TTS_TURN_MAX", "12"))
# Storylines + framing run when the GPU is idle, or at least this often under load.
ENRICH_MAX_LAG_SECONDS = float(os.environ.get("ENRICH_MAX_LAG_SECONDS", "900"))

PUBLISH_ENABLED = _flag("PUBLISH_ENABLED", "true")
PUBLISH_REQUIRE_AUDIO = _flag("PUBLISH_REQUIRE_AUDIO", "false")
MONGODB_URI = os.environ.get("MONGODB_URI", "mongodb://127.0.0.1:27017")
MONGODB_DATABASE = os.environ.get("MONGODB_DATABASE", "cnews")
S3_ENDPOINT = os.environ.get("S3_ENDPOINT", "http://127.0.0.1:9000")
S3_REGION = os.environ.get("S3_REGION", "ca-central-1")
S3_BUCKET = os.environ.get("S3_BUCKET", "cnews-audio")
S3_ACCESS_KEY = os.environ.get("S3_ACCESS_KEY", "cnewsminio")
S3_SECRET_KEY = os.environ.get("S3_SECRET_KEY", "cnewsminio")
S3_FORCE_PATH_STYLE = _flag("S3_FORCE_PATH_STYLE", "true")
S3_PREFIX = os.environ.get("S3_PREFIX", "audio/opus")

# Local working store: article text is dropped once briefed and audio once uploaded.
# The small row stays this long so a URL an RSS feed still lists is not briefed twice
# (matches the 7-day seen window; going lower brings duplicates back).
RETENTION_DAYS = max(int(os.environ.get("RETENTION_DAYS", "7")), SEEN_TTL_SECONDS // 86400)
# Published store (MongoDB + S3): what the app can still show.
PRUNE_PUBLISHED = _flag("PRUNE_PUBLISHED", "true")
STORY_RETENTION_DAYS = int(os.environ.get("STORY_RETENTION_DAYS", "14"))
CLOSED_STORYLINE_RETENTION_DAYS = int(os.environ.get("CLOSED_STORYLINE_RETENTION_DAYS", "30"))
# Open storylines with no update for this long are closed automatically.
STORYLINE_STALE_DAYS = int(os.environ.get("STORYLINE_STALE_DAYS", "7"))
MAINTENANCE_INTERVAL_SECONDS = int(os.environ.get("MAINTENANCE_INTERVAL_SECONDS", "3600"))
# Heartbeat to MongoDB so GET /v1/health/ingest can alert when this box stops.
HEARTBEAT_INTERVAL_SECONDS = int(os.environ.get("HEARTBEAT_INTERVAL_SECONDS", "60"))
# How often to retry audio that rendered but failed to upload to S3.
UPLOAD_RETRY_INTERVAL_SECONDS = int(os.environ.get("UPLOAD_RETRY_INTERVAL_SECONDS", "600"))

UI_HOST = os.environ.get("UI_HOST", "127.0.0.1")
UI_PORT = int(os.environ.get("UI_PORT", "8765"))

# Keep each poll short so summaries show up while the rest of the feed waits.
# With dozens of feeds, two new stories per poll keeps the local model from falling behind.
MAX_NEW_ARTICLES_PER_POLL = 2
ARTICLE_FETCH_CONCURRENCY = 3
# Feeds fetched at once in one polling round (I/O only; briefs are still one at a time).
FEED_POLL_CONCURRENCY = int(os.environ.get("FEED_POLL_CONCURRENCY", "6"))
# Pause new-article intake while this many articles wait for a brief (0 = never pause).
ARTICLE_BACKLOG_MAX = int(os.environ.get("ARTICLE_BACKLOG_MAX", "40"))
PROMPT_CHAR_LIMIT = 4500

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
)
