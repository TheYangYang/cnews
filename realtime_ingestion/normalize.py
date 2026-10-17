"""HTML cleanup, ticker expansion, and article text extraction."""

from __future__ import annotations

import hashlib
import html
import json
import re
import unicodedata
from html.parser import HTMLParser
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

DROP_QUERY_KEYS = {
    "cmp",
    "fbclid",
    "gclid",
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
}

# Spoken forms for tickers that show up in business copy ($NVDA -> Nvidia).
TICKERS = {
    "AAPL": "Apple",
    "AMZN": "Amazon",
    "AMD": "AMD",
    "ATD": "Alimentation Couche-Tard",
    "BAM": "Brookfield",
    "BB": "BlackBerry",
    "BCE": "Bell",
    "BMO": "BMO",
    "BN": "Brookfield",
    "BNS": "Scotiabank",
    "CM": "CIBC",
    "CNQ": "Canadian Natural Resources",
    "CNR": "Canadian National Railway",
    "CP": "Canadian Pacific",
    "CSCO": "Cisco",
    "CVE": "Cenovus",
    "ENB": "Enbridge",
    "GOOGL": "Alphabet",
    "IMO": "Imperial Oil",
    "INTC": "Intel",
    "META": "Meta",
    "MSFT": "Microsoft",
    "NTR": "Nutrien",
    "NVDA": "Nvidia",
    "RY": "Royal Bank of Canada",
    "SHOP": "Shopify",
    "SU": "Suncor",
    "T": "Telus",
    "TD": "TD Bank",
    "TRI": "Thomson Reuters",
    "TSLA": "Tesla",
    "WCN": "Waste Connections",
}

# Longer tokens first so "P.E.I." is not partially rewritten.
ABBREVIATIONS = [
    ("P.E.I.", "Prince Edward Island"),
    ("N.W.T.", "Northwest Territories"),
    ("B.C.", "British Columbia"),
    ("Sask.", "Saskatchewan"),
    ("Alta.", "Alberta"),
    ("Ont.", "Ontario"),
    ("Que.", "Quebec"),
    ("Man.", "Manitoba"),
    ("N.B.", "New Brunswick"),
    ("N.S.", "Nova Scotia"),
    ("N.L.", "Newfoundland and Labrador"),
    ("Y.T.", "Yukon"),
    ("MLA", "Member of the Legislative Assembly"),
    ("MPP", "Member of Provincial Parliament"),
    ("RCMP", "Royal Canadian Mounted Police"),
    ("CBSA", "Canada Border Services Agency"),
    ("CRA", "Canada Revenue Agency"),
    ("UCP", "United Conservative Party"),
    ("NDP", "New Democratic Party"),
    ("CPC", "Conservative Party of Canada"),
    ("GTA", "Greater Toronto Area"),
    ("OPP", "Ontario Provincial Police"),
    ("GST", "goods and services tax"),
    ("MP", "Member of Parliament"),
    ("PM", "Prime Minister"),
]


def canonical_url(url: str) -> str:
    parts = urlsplit(url.strip())
    query = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if key.lower() not in DROP_QUERY_KEYS and not key.lower().startswith("utm_")
    ]
    path = parts.path.rstrip("/") or "/"
    return urlunsplit(
        (parts.scheme.lower(), parts.netloc.lower(), path, urlencode(query), "")
    )


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def title_hash(title: str) -> str:
    folded = unicodedata.normalize("NFKC", title).lower()
    folded = re.sub(r"[^a-z0-9]+", " ", folded).strip()
    return digest(folded)


# Words that show up in almost every headline and should not glue two stories together.
_TITLE_STOPWORDS = {
    "a", "an", "the", "and", "or", "of", "to", "in", "on", "for", "with", "at", "by",
    "from", "as", "after", "over", "into", "its", "it", "be", "is", "are", "was",
    "were", "that", "this", "these", "those", "new", "says", "say", "said", "will",
    "has", "have", "had", "not", "but", "his", "her", "their", "who", "what", "when",
    "how", "why", "about", "more", "than", "they", "them", "been", "can", "could",
    "would", "should", "may", "might", "also", "just", "up", "out", "our", "your",
    "amid", "versus", "under", "across", "during", "while", "before", "since",
    "canada", "canadian", "canadians",
}


def content_tokens(title: str) -> set[str]:
    folded = unicodedata.normalize("NFKC", title).lower()
    folded = re.sub(r"[^a-z0-9]+", " ", folded)
    return {token for token in folded.split() if len(token) >= 3 and token not in _TITLE_STOPWORDS}


def same_story(left: str, right: str) -> bool:
    """True when two headlines are close enough to be the same news event.

    Outlets rarely use the same wording, so a shared set of distinctive words
    is enough. Two shared words are not, because those are often just the topic.
    """
    first = content_tokens(left)
    second = content_tokens(right)
    if not first or not second:
        return False
    if first == second:
        return True
    shared = first & second
    if len(shared) < 3:
        return False
    # One swapped word on a short headline is often the opposite update
    # ("holds" versus "cuts"), so leave those as separate stories.
    if len(first - second) == 1 and len(second - first) == 1 and len(shared) < 4:
        return False
    if first <= second or second <= first:
        return True
    smaller = min(len(first), len(second))
    overlap = len(shared) / smaller
    if len(shared) >= 4 and overlap >= 0.5:
        return True
    distinctive = sum(1 for token in shared if len(token) >= 5)
    return distinctive >= 2 and overlap >= 0.4


def html_to_text(value: str) -> str:
    text = html.unescape(value or "")
    text = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def extract_image(fragment: str) -> str | None:
    match = re.search(r"<img[^>]+src=['\"]([^'\"]+)['\"]", fragment or "", re.I)
    if not match:
        return None
    src = html.unescape(match.group(1))
    if src.startswith("https://"):
        return src
    return None


class _StoryParser(HTMLParser):
    """Pull paragraph text out of CBC's story column."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.depth = 0
        self.capture_until: int | None = None
        self.skip = 0
        self.in_paragraph = False
        self.buffer: list[str] = []
        self.paragraphs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.depth += 1
        if tag in {"script", "style", "noscript"}:
            self.skip += 1
            return
        class_name = ""
        for key, value in attrs:
            if key == "class" and value:
                class_name = value
        if self.capture_until is None and (
            "detailBodyContainer" in class_name or "sclt-storycontent" in class_name
        ):
            self.capture_until = self.depth
        if self.capture_until is not None and self.skip == 0 and tag == "p":
            self.in_paragraph = True
            self.buffer = []

    def handle_endtag(self, tag: str) -> None:
        if self.capture_until is not None and self.in_paragraph and tag == "p":
            text = re.sub(r"\s+", " ", "".join(self.buffer)).strip()
            if len(text) >= 20:
                self.paragraphs.append(text)
            self.in_paragraph = False
            self.buffer = []
        if tag in {"script", "style", "noscript"} and self.skip:
            self.skip -= 1
        if self.capture_until is not None and self.depth == self.capture_until:
            self.capture_until = None
        self.depth = max(0, self.depth - 1)

    def handle_data(self, data: str) -> None:
        if self.capture_until is not None and self.skip == 0 and self.in_paragraph:
            self.buffer.append(data)


def _decode_json_string(raw: str) -> str:
    try:
        text = json.loads(f'"{raw}"')
    except json.JSONDecodeError:
        return ""
    if not isinstance(text, str):
        return ""
    return re.sub(r"\s+", " ", text).strip()


def _embedded_bodies(page_html: str) -> str:
    """CBC live stories keep the copy in JSON instead of article paragraphs."""
    seen: set[str] = set()
    chunks: list[str] = []
    for raw in re.findall(r'"articleBody"\s*:\s*"((?:\\.|[^"\\])*)"', page_html):
        text = _decode_json_string(raw)
        if len(text) < 40 or text in seen:
            continue
        seen.add(text)
        chunks.append(text)
        if len(chunks) >= 8:
            break
    return "\n\n".join(chunks).strip()


def _meta_description(page_html: str) -> str:
    patterns = (
        r'<meta[^>]+(?:property|name)=["\'](?:og:description|description)["\'][^>]+content=["\']([^"\']+)',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:property|name)=["\'](?:og:description|description)["\']',
    )
    for pattern in patterns:
        match = re.search(pattern, page_html, re.I)
        if match:
            return re.sub(r"\s+", " ", html.unescape(match.group(1))).strip()
    return ""


def extract_story(page_html: str) -> str:
    parser = _StoryParser()
    parser.feed(page_html)
    paragraphs: list[str] = []
    for paragraph in parser.paragraphs:
        lowered = paragraph.lower()
        if lowered.startswith(
            ("share this", "related stories", "corrections and clarifications", "sign up")
        ):
            continue
        paragraphs.append(paragraph)
        if len(paragraphs) >= 40:
            break
    story = "\n\n".join(paragraphs).strip()
    if len(story) >= 200:
        return story
    embedded = _embedded_bodies(page_html)
    if len(embedded) > len(story):
        return embedded
    if story:
        return story
    return _meta_description(page_html)


def _expand_tickers(text: str) -> str:
    def replace(match: re.Match[str]) -> str:
        symbol = match.group(1)
        return TICKERS.get(symbol, symbol)

    return re.sub(r"\$([A-Z]{1,5})\b", replace, text)


def _expand_abbreviations(text: str) -> str:
    for token, spoken in ABBREVIATIONS:
        text = re.sub(rf"(?<!\w){re.escape(token)}(?!\w)", spoken, text)
    return text


def prepare_speech_text(value: str, *, limit: int = 8000) -> str:
    text = html.unescape(value or "")
    text = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = unicodedata.normalize("NFKC", text)
    text = (
        text.replace("\u00a0", " ")
        .replace("\u2018", "'")
        .replace("\u2019", "'")
        .replace("\u201c", '"')
        .replace("\u201d", '"')
    )
    text = _expand_tickers(text)
    text = _expand_abbreviations(text)
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > limit:
        text = text[:limit].rsplit(" ", 1)[0]
    return text


def tidy_summary(value: str, *, max_words: int = 60) -> str:
    text = re.sub(r"(?is)<think>.*?</think>", " ", value or "")
    text = text.strip().strip('"').strip()
    text = re.sub(
        r"(?i)^(?:(?:good (?:morning|afternoon|evening|night)[,.]?\s*)?(?:i(?:'m| am) reporting from [^.]+\.\s*)|(?:here(?:'s| is)(?: a)?|summary|spoken brief|a \d+-word(?: news)? brief)\b[:\s-]*)",
        "",
        text,
    ).strip()
    text = re.sub(r"[#*_`]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    words = text.split()
    if len(words) > max_words:
        chunk = " ".join(words[:max_words])
        period = max(chunk.rfind(". "), chunk.rfind("? "), chunk.rfind("! "))
        if period >= int(len(chunk) * 0.55):
            text = chunk[: period + 1].strip()
        else:
            text = chunk.rstrip(",;: ") + "."
    return text


def word_count(value: str) -> int:
    return len((value or "").split())
