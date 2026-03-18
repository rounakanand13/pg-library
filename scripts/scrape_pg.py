#!/usr/bin/env python3

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
from urllib.parse import urljoin, urlsplit

import requests
from bs4 import BeautifulSoup


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = PROJECT_ROOT / "data" / "essays.json"
INDEX_URL = "https://paulgraham.com/articles.html"
MONTH_PATTERN = (
    "January|February|March|April|May|June|July|August|September|October|November|December"
)
DATE_RE = re.compile(rf"^({MONTH_PATTERN})\s+\d{{4}}$")
YEAR_RE = re.compile(r"(19|20)\d{2}")
TRANSLATION_RE = re.compile(r"translation", re.IGNORECASE)
SESSION = requests.Session()
SESSION.headers.update(
    {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/123.0 Safari/537.36"
        )
    }
)


def normalize_space(value: str) -> str:
    value = value.replace("\xa0", " ").replace("\r", "\n")
    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()


def comparable(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "essay"


def split_sentences(value: str) -> list[str]:
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+", value) if part.strip()]


def is_boilerplate(value: str) -> bool:
    lower = value.lower()
    return lower.startswith("want to start a startup? get funded by y combinator")


def read_index() -> list[dict]:
    response = SESSION.get(INDEX_URL, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    essays: list[dict] = []
    seen_hrefs: set[str] = set()

    for anchor in soup.find_all("a", href=True):
        href = anchor["href"].strip()
        title = normalize_space(anchor.get_text(" ", strip=True))
        href_path = urlsplit(href).path.lower()

        if not title:
            continue
        if href.startswith(("mailto:", "#")):
            continue
        if not href_path.endswith((".html", ".txt")):
            continue
        if href in {"articles.html", "index.html", "rss.html"}:
            continue
        source_url = urljoin(INDEX_URL, href)
        if source_url in seen_hrefs:
            continue

        seen_hrefs.add(source_url)
        essays.append(
            {
                "href": href,
                "title": title,
                "source_url": source_url,
                "source_order": len(essays) + 1,
            }
        )

    if not essays:
        raise RuntimeError("No essay links were found on the Paul Graham index page.")

    return essays


def longest_candidate(soup: BeautifulSoup):
    candidates = [
        tag
        for tag in soup.find_all(["font", "td", "article"])
        if len(normalize_space(tag.get_text(" ", strip=True))) > 200
    ]
    if not candidates:
        return soup.body or soup

    def score(tag) -> int:
        text = normalize_space(tag.get_text(" ", strip=True))
        return len(text)

    return max(candidates, key=score)


def extract_blocks(container: BeautifulSoup) -> list[str]:
    for tag in container.find_all(["script", "style", "noscript"]):
        tag.decompose()
    for br in container.find_all("br"):
        br.replace_with("\n")

    text = container.get_text()
    blocks: list[str] = []
    for chunk in re.split(r"\n\s*\n+", text):
        lines = [normalize_space(line) for line in chunk.splitlines()]
        lines = [line for line in lines if line]
        if not lines:
            continue
        blocks.append(" ".join(lines))
    return blocks


def extract_date(blocks: list[str]) -> tuple[str | None, list[str]]:
    for index, block in enumerate(blocks[:8]):
        if looks_like_date(block):
            return block, blocks[:index] + blocks[index + 1 :]
    return None, blocks


def looks_like_date(value: str) -> bool:
    if not value or len(value) > 100:
        return False
    if "translation" in value.lower():
        return False
    if re.fullmatch(r"\d{4}", value):
        return True
    return bool(re.search(rf"\b({MONTH_PATTERN})\b", value) and YEAR_RE.search(value))


def extract_top_date(lines: list[str]) -> str | None:
    for line in lines[:40]:
        if looks_like_date(line):
            return line
    return None


def extract_title_offset(blocks: list[str], title: str) -> int:
    target = comparable(title)
    for index, block in enumerate(blocks[:10]):
        current = comparable(block)
        if current == target or target in current or current in target:
            return index
    return -1


def find_translations(soup: BeautifulSoup, base_url: str) -> list[dict]:
    translations: list[dict] = []
    seen: set[str] = set()
    for anchor in soup.find_all("a", href=True):
        label = normalize_space(anchor.get_text(" ", strip=True))
        if not label or not TRANSLATION_RE.search(label):
            continue
        href = urljoin(base_url, anchor["href"])
        if href in seen:
            continue
        seen.add(href)
        translations.append({"label": label, "url": href})
    return translations


def parse_date_parts(date_text: str | None) -> tuple[int | None, int | None, str | None]:
    if not date_text:
        return None, None, None

    try:
        parsed = datetime.strptime(date_text, "%B %Y")
        return parsed.year, parsed.month, parsed.strftime("%Y-%m-01")
    except ValueError:
        match = YEAR_RE.search(date_text)
        year = int(match.group(0)) if match else None
        return year, None, None


def pick_pull_quote(paragraphs: Iterable[str]) -> str | None:
    for paragraph in paragraphs:
        if len(paragraph) < 80:
            continue
        for sentence in split_sentences(paragraph):
            if 80 <= len(sentence) <= 220:
                return sentence
    return None


def paragraph_score(paragraphs: list[str]) -> tuple[int, int, int]:
    total_words = sum(len(paragraph.split()) for paragraph in paragraphs)
    substantial = sum(1 for paragraph in paragraphs if len(paragraph.split()) >= 25)
    return substantial, total_words, -len(paragraphs)


def clean_blocks(blocks: list[str], title: str) -> tuple[str | None, list[str]]:
    thanks: str | None = None
    paragraphs: list[str] = []

    for block in blocks:
        if not block:
            continue
        if is_boilerplate(block):
            continue
        if comparable(block) == comparable(title):
            continue
        if looks_like_date(block):
            continue
        if TRANSLATION_RE.search(block) and len(block.split()) <= 20 and "." not in block:
            continue
        lower = block.lower()
        if lower.startswith("thanks to") or lower.startswith("special thanks to"):
            thanks = block
            continue
        paragraphs.append(block)

    return thanks, paragraphs


def trim_intro_lines(lines: list[str], title: str, date_text: str | None) -> list[str]:
    trimmed = list(lines)
    title_offset = extract_title_offset(trimmed, title)
    if title_offset >= 0:
        trimmed = trimmed[title_offset + 1 :]

    if date_text:
        for index, line in enumerate(trimmed[:12]):
            if line == date_text:
                trimmed = trimmed[index + 1 :]
                break

    return trimmed


def coalesce_lines(lines: list[str]) -> list[str]:
    blocks: list[str] = []
    buffer: list[str] = []

    for line in lines:
        if not line:
            continue

        if not buffer:
            buffer = [line]
            continue

        previous = buffer[-1]
        should_join = (
            len(line.split()) <= 3
            or len(previous.split()) <= 3
            or previous[-1] not in ".!?)”]"
        )

        if should_join:
            buffer.append(line)
        else:
            blocks.append(normalize_space(" ".join(buffer)))
            buffer = [line]

    if buffer:
        blocks.append(normalize_space(" ".join(buffer)))

    return [block for block in blocks if block]


def scrape_essay(entry: dict) -> dict:
    response = SESSION.get(entry["source_url"], timeout=30)
    response.raise_for_status()
    if response.apparent_encoding:
        response.encoding = response.apparent_encoding

    soup = BeautifulSoup(response.text, "html.parser")
    top_lines = [
        normalize_space(line)
        for line in soup.get_text("\n").splitlines()
        if normalize_space(line)
    ]
    top_date = extract_top_date(top_lines)
    candidate = BeautifulSoup(str(longest_candidate(soup)), "html.parser")
    blocks = extract_blocks(candidate)
    page_blocks = extract_blocks(BeautifulSoup(str(soup.body or soup), "html.parser"))

    title_offset = extract_title_offset(blocks, entry["title"])
    if title_offset >= 0:
        blocks = blocks[title_offset + 1 :]

    date_text, blocks = extract_date(blocks)
    date_text = date_text or top_date
    thanks, paragraphs = clean_blocks(blocks, entry["title"])

    fallback_blocks = trim_intro_lines(page_blocks, entry["title"], date_text)
    fallback_thanks, fallback_paragraphs = clean_blocks(fallback_blocks, entry["title"])

    if paragraph_score(fallback_paragraphs) > paragraph_score(paragraphs):
        thanks, paragraphs = fallback_thanks, fallback_paragraphs

    line_blocks = coalesce_lines(trim_intro_lines(top_lines, entry["title"], date_text))
    line_thanks, line_paragraphs = clean_blocks(line_blocks, entry["title"])

    if paragraph_score(line_paragraphs) > paragraph_score(paragraphs):
        thanks, paragraphs = line_thanks, line_paragraphs

    if not paragraphs:
        raise RuntimeError(f"No paragraph content extracted for {entry['source_url']}")

    year, month, sort_date = parse_date_parts(date_text)
    word_count = sum(len(paragraph.split()) for paragraph in paragraphs)
    reading_minutes = max(1, round(word_count / 230))
    excerpt = next((p for p in paragraphs if len(p) >= 120), paragraphs[0])
    pull_quote = pick_pull_quote(paragraphs) or excerpt
    slug = slugify(entry["title"])

    return {
        "title": entry["title"],
        "slug": slug,
        "href": entry["href"],
        "source_url": entry["source_url"],
        "source_order": entry["source_order"],
        "chapter_number": entry["source_order"],
        "date_text": date_text,
        "year": year,
        "month": month,
        "sort_date": sort_date,
        "excerpt": excerpt,
        "pull_quote": pull_quote,
        "thanks": thanks,
        "word_count": word_count,
        "reading_minutes": reading_minutes,
        "paragraph_count": len(paragraphs),
        "translations": find_translations(soup, entry["source_url"]),
        "paragraphs": paragraphs,
    }


def ensure_unique_slugs(essays: list[dict]) -> None:
    seen: dict[str, int] = {}
    for essay in essays:
        slug = essay["slug"]
        if slug not in seen:
            seen[slug] = 1
            continue
        seen[slug] += 1
        essay["slug"] = f"{slug}-{seen[slug]}"


def main() -> None:
    index_entries = read_index()
    essays = [scrape_essay(entry) for entry in index_entries]
    ensure_unique_slugs(essays)

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_index_url": INDEX_URL,
        "essay_count": len(essays),
        "essays": essays,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(essays)} essays to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
