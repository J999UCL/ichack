from __future__ import annotations

import html
import io
import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import Config

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

# --------------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------------- #

CONTENT_TERMS: List[str] = [
    "article",
    "blog",
    "post",
    "guide",
    "tutorial",
    "essay",
    "story",
    "origin",
    "history",
]
EXCLUDED_DOMAINS: List[str] = [
    "youtube.com",
    "facebook.com",
    "twitter.com",
    "instagram.com",
    "tiktok.com",
    "pinterest.com",
    "linkedin.com",
]
# file types we *still* want to reject (videos, slides, etc.)
EXCLUDED_EXTENSIONS: List[str] = [
    ".ppt",
    ".pptx",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".mp4",
    ".avi",
    ".mov",
]
MIME_HINTS: List[str] = ["video", "playlist", "watch", "login", "signup"]

# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


@dataclass(slots=True, frozen=True)
class _Result:
    title: str
    url: str
    snippet: str
    image: str
    source: str

    def asdict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "image": self.image,
            "source": self.source,
        }


def _retry() -> Retry:
    return Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods={"GET"},
    )


def _domain(url: str) -> str:
    try:
        return urlparse(url).netloc.replace("www.", "")
    except Exception:
        return ""


def _has_content_term(text: str) -> bool:
    text = text.lower()
    return any(term in text for term in CONTENT_TERMS)


def _has_keyword(text: str) -> bool:
    kw_list: List[str] = getattr(Config, "SEARCH_KEYWORDS", [])
    if not kw_list:
        return True
    lowered = text.lower()
    return any(k.lower() in lowered for k in kw_list)


def _looks_like_file(url: str) -> bool:
    lowered = url.lower()
    return any(lowered.endswith(ext) for ext in EXCLUDED_EXTENSIONS)


def _mime_hint(url: str) -> bool:
    lowered = url.lower()
    return any(hint in lowered for hint in MIME_HINTS)


def _is_pdf(url: str, ctype: str | None = None) -> bool:
    if ctype and "application/pdf" in ctype.lower():
        return True
    return url.lower().endswith(".pdf")


# --------------------------------------------------------------------------- #
# Client
# --------------------------------------------------------------------------- #


class GoogleSearchAPI:
    """Handles Google Custom Search API interactions."""

    BASE_URL = "https://www.googleapis.com/customsearch/v1"
    _PAGE_SIZE = 10
    _TIMEOUT = (5, 15)

    def __init__(self) -> None:
        self.api_key: str = Config.GOOGLE_SEARCH_API_KEY
        self.search_engine_id: str = Config.GOOGLE_SEARCH_ENGINE_ID

        if not self.api_key or not self.search_engine_id:
            raise ValueError(
                "Google Search API credentials are missing "
                "(Config.GOOGLE_SEARCH_API_KEY / GOOGLE_SEARCH_ENGINE_ID)."
            )

        self._session = requests.Session()
        self._session.headers.update(
            {
                "User-Agent": "OriginExplorer/3.1 (strict-text+pdf)",
                "Accept": "application/json",
            }
        )
        adapter = HTTPAdapter(max_retries=_retry())
        self._session.mount("https://", adapter)
        self._session.mount("http://", adapter)

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def search_articles(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Return up to *limit* relevant HTML/PDF article results for *query*."""
        if not query:
            raise ValueError("Query may not be empty")

        try:
            results: List[_Result] = []
            pages = min((limit - 1) // self._PAGE_SIZE + 1, 10)

            for page in range(pages):
                start = page * self._PAGE_SIZE + 1
                data = self._call_google(query, limit, start)

                for item in data.get("items", []):
                    article = self._format(item)
                    if self._is_relevant(article):
                        results.append(article)
                        if len(results) >= limit:
                            break

                if len(results) >= limit:
                    break

            return [r.asdict() for r in results[:limit]]

        except Exception as exc:
            logger.exception("search_articles failed: %s", exc)
            raise ValueError("Search API Failed") from exc

    def get_article_content(self, url: str) -> Optional[str]:
        """
        Fetch article text (HTML or PDF) from *url*.

        Returns up to 2 000 characters, raising ``ValueError`` on any problem.
        """
        if not url:
            raise ValueError("URL may not be empty")

        if _looks_like_file(url) or _mime_hint(url):
            raise ValueError("Unsupported file type")

        try:
            resp = self._session.get(url, timeout=self._TIMEOUT, stream=True)
            resp.raise_for_status()
            ctype = resp.headers.get("Content-Type", "")
            if _is_pdf(url, ctype):
                text = self._extract_pdf(resp.content)
            else:
                text = self._extract_html(resp.text)
            return text[:2000] if text else None
        except Exception as exc:
            logger.exception("get_article_content failed: %s", exc)
            raise ValueError(f"Failed to fetch content from {url}") from exc

    def is_available(self) -> bool:  # public contract unchanged
        return True

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #

    def _call_google(self, query: str, limit: int, start: int) -> Dict[str, Any]:
        params = {
            "key": self.api_key,
            "cx": self.search_engine_id,
            "q": f"{query} (origin OR history) (article OR blog OR guide OR tutorial)",
            "num": min(limit, self._PAGE_SIZE),
            "start": start,
            "safe": "active",
            "fields": (
                "items(title,link,snippet,pagemap(cse_image,metatags)),"
                "queries(nextPage)"
            ),
        }

        resp = self._session.get(self.BASE_URL, params=params, timeout=self._TIMEOUT)
        resp.raise_for_status()
        return resp.json()

    # ---------------- text extraction ---------------- #

    @staticmethod
    def _extract_html(raw_html: str) -> str:
        """Simple readability extraction from HTML."""
        try:
            from bs4 import BeautifulSoup  # type: ignore
        except ModuleNotFoundError:
            text = re.sub(r"<[^>]+>", " ", raw_html)
            return re.sub(r"\s+", " ", html.unescape(text)).strip()

        soup = BeautifulSoup(raw_html, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        return re.sub(r"\s+", " ", soup.get_text(" ", strip=True))

    @staticmethod
    def _extract_pdf(binary: bytes) -> str:
        """Extract text from a PDF binary, using pdfminer.six or PyPDF2."""
        # Try pdfminer.six first
        try:
            from pdfminer.high_level import extract_text  # type: ignore
            text = extract_text(io.BytesIO(binary))
            if text:
                return re.sub(r"\s+", " ", text)
        except Exception as exc:
            logger.debug("pdfminer.six failed: %s", exc)

        # Fallback to PyPDF2
        try:
            from PyPDF2 import PdfReader  # type: ignore
            reader = PdfReader(io.BytesIO(binary))
            pages_text = [page.extract_text() or "" for page in reader.pages]
            text = " ".join(pages_text)
            return re.sub(r"\s+", " ", text)
        except Exception as exc:  # pragma: no cover
            logger.debug("PyPDF2 failed: %s", exc)

        raise ValueError("Unable to parse PDF – install pdfminer.six or PyPDF2")

    # ---------------- result helpers ---------------- #

    def _is_relevant(self, art: _Result) -> bool:
        blob = f"{art.title} {art.snippet} {art.url}".lower()
        return (
            _has_content_term(blob)
            and _has_keyword(blob)
            and not _looks_like_file(art.url)
            and not _mime_hint(art.url)
            and not any(dom in art.url.lower() for dom in EXCLUDED_DOMAINS)
        )

    @staticmethod
    def _format(item: Dict[str, Any]) -> _Result:
        pagemap = item.get("pagemap", {})
        img = ""
        if pagemap.get("cse_image"):
            img = pagemap["cse_image"][0].get("src", "")
        elif pagemap.get("metatags"):
            mt = pagemap["metatags"][0]
            img = (
                mt.get("og:image", "")
                or mt.get("twitter:image", "")
                or mt.get("image", "")
            )

        return _Result(
            title=item.get("title", "Untitled"),
            url=item.get("link", ""),
            snippet=item.get("snippet", "No description available"),
            image=img,
            source=_domain(item.get("link", "")),
        )