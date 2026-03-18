#!/usr/bin/env python3

from __future__ import annotations

import json
import os
from datetime import datetime
from html import escape
from pathlib import Path
from shutil import copy2


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = PROJECT_ROOT / "data" / "essays.json"
DIST_DIR = PROJECT_ROOT / "dist"
ASSETS_DIR = PROJECT_ROOT / "src" / "assets"
DIST_ASSETS_DIR = DIST_DIR / "assets"


def load_payload() -> dict:
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Missing scraped data at {DATA_PATH}")
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def format_number(value: int) -> str:
    return f"{value:,}"


def relative_asset(path: str, depth: int) -> str:
    prefix = "../" * depth
    return f"{prefix}{path}"


def chapter_href(slug: str, depth: int = 0) -> str:
    prefix = "../" * depth
    return f"{prefix}essays/{slug}/" if depth == 0 else f"{prefix}{slug}/"


def shell(
    *,
    page_title: str,
    description: str,
    body_html: str,
    depth: int,
    asset_version: str,
    body_attrs: str = "",
) -> str:
    styles_href = f"{relative_asset('assets/styles.css', depth)}?v={asset_version}"
    script_href = f"{relative_asset('assets/app.js', depth)}?v={asset_version}"
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="theme-color" content="#0d1722">
  <meta name="description" content="{escape(description)}">
  <title>{escape(page_title)}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600;9..144,700&family=IBM+Plex+Mono:wght@400;500&family=Instrument+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="{escape(styles_href)}">
  <script defer src="{escape(script_href)}"></script>
</head>
<body {body_attrs}>
  <div class="ambient ambient--one"></div>
  <div class="ambient ambient--two"></div>
  <div class="noise"></div>
  {body_html}
</body>
</html>
"""


def render_home(essays: list[dict], payload: dict) -> str:
    years = [essay["year"] for essay in essays if essay["year"]]
    min_year = min(years)
    max_year = max(years)
    total_minutes = sum(essay["reading_minutes"] for essay in essays)
    total_words = sum(essay["word_count"] for essay in essays)
    featured = essays[:4]
    year_filters = sorted({essay["year"] for essay in essays if essay["year"]}, reverse=True)

    stack = "".join(
        f"""
        <div class="book-spine" style="--spine-index:{index};">
          <span>{escape(essay["title"])}</span>
        </div>
        """
        for index, essay in enumerate(essays[:8])
    )

    spotlight = "".join(
        f"""
        <a class="spotlight-card reveal" href="{escape(chapter_href(essay['slug']))}">
          <span class="eyebrow">Chapter {essay['chapter_number']:03d}</span>
          <h3>{escape(essay['title'])}</h3>
          <p>{escape(essay['excerpt'])}</p>
          <div class="spotlight-meta">
            <span>{escape(essay['date_text'] or str(essay['year']))}</span>
            <span>{essay['reading_minutes']} min</span>
          </div>
        </a>
        """
        for essay in featured
    )

    chapter_cards = "".join(
        f"""
        <article
          class="chapter-card reveal"
          data-search="{escape((essay['title'] + ' ' + essay['excerpt']).lower())}"
          data-year="{escape(str(essay['year'] or 'Unknown'))}">
          <a class="chapter-card__link" href="{escape(chapter_href(essay['slug']))}">
            <div class="chapter-card__topline">
              <span>Chapter {essay['chapter_number']:03d}</span>
              <span>{escape(str(essay['year'] or 'Undated'))}</span>
            </div>
            <h3>{escape(essay['title'])}</h3>
            <p>{escape(essay['excerpt'])}</p>
            <div class="chapter-card__footer">
              <span>{essay['reading_minutes']} min read</span>
              <span>{format_number(essay['word_count'])} words</span>
            </div>
          </a>
        </article>
        """
        for essay in essays
    )

    filters = "".join(
        f'<button class="filter-pill" type="button" data-year-filter="{year}">{year}</button>'
        for year in year_filters
    )

    generated_at = datetime.fromisoformat(payload["generated_at"].replace("Z", "+00:00"))

    return f"""
    <div class="reading-progress reading-progress--home"><span></span></div>
    <header class="site-header">
      <a class="brand" href="./">PG / Library</a>
      <nav class="site-nav">
        <a href="#chapters">Chapters</a>
        <a href="#source">Source</a>
      </nav>
    </header>

    <main class="home-shell">
      <section class="hero reveal">
        <div class="hero-copy">
          <span class="eyebrow">Collected Essays</span>
          <h1>The sharpest essays in Silicon Valley, bound like a proper volume.</h1>
          <p class="hero-copy__lede">
            Paul Graham writes about startups, wealth, taste, language, ambition, and work with the
            rare habit of saying something useful in every paragraph. Read the full archive in one
            handsome edition, built for long attention instead of hurried skimming.
          </p>
          <div class="hero-actions">
            <a class="button button--primary" href="#chapters">Browse Chapters</a>
            <a class="button button--secondary" href="{escape(payload['source_index_url'])}">Original Index</a>
          </div>
        </div>
        <div class="hero-stack" aria-hidden="true">
          {stack}
        </div>
      </section>

      <section class="stats-band reveal">
        <article class="stat-card">
          <span class="stat-card__label">Chapter Count</span>
          <strong>{format_number(len(essays))}</strong>
          <p>Every essay currently listed on Paul Graham’s index page.</p>
        </article>
        <article class="stat-card">
          <span class="stat-card__label">Archive Span</span>
          <strong>{min_year} to {max_year}</strong>
          <p>{max_year - min_year + 1} years of essays gathered into one reading surface.</p>
        </article>
        <article class="stat-card">
          <span class="stat-card__label">Reading Depth</span>
          <strong>{total_minutes // 60} hrs</strong>
          <p>{format_number(total_words)} words across the full collection.</p>
        </article>
      </section>

      <section class="spotlight reveal">
        <div class="section-heading">
          <span class="eyebrow">Current Shelf</span>
          <h2>Recent chapters, staged like a flagship archive.</h2>
        </div>
        <div class="spotlight-grid">
          {spotlight}
        </div>
      </section>

      <section class="library reveal" id="chapters">
        <div class="library-header">
          <div class="section-heading">
            <span class="eyebrow">Contents</span>
            <h2>The full table of contents.</h2>
          </div>
          <div class="search-panel">
            <label class="search-field">
              <span class="search-field__label">Search</span>
              <input type="search" placeholder="Search by title or excerpt" data-search-input>
            </label>
            <div class="library-counter" data-results-count>{len(essays)} chapters</div>
          </div>
        </div>
        <div class="filters" role="toolbar" aria-label="Filter chapters by year">
          <button class="filter-pill is-active" type="button" data-year-filter="all">All years</button>
          {filters}
        </div>
        <div class="chapter-grid" data-chapter-grid>
          {chapter_cards}
        </div>
      </section>

      <section class="source-note reveal" id="source">
        <div class="section-heading">
          <span class="eyebrow">Source</span>
          <h2>Built from the live archive, with the older `avyfain/pg-essays` repo audited as a safe reference.</h2>
        </div>
        <p>
          This site was generated on {escape(generated_at.strftime("%B %d, %Y at %H:%M UTC"))} from
          <a href="{escape(payload['source_index_url'])}">paulgraham.com/articles.html</a>. The GitHub repo
          <a href="https://github.com/avyfain/pg-essays">avyfain/pg-essays</a> was inspected and found to be a
          small Python scraper and analysis project with no malicious behavior; its extraction approach informed
          the modernized ingestion pipeline, but this site does not depend on that code at runtime.
        </p>
      </section>
    </main>
    """


def render_chapter_page(
    essay: dict, prev_essay: dict | None, next_essay: dict | None, peers: list[dict]
) -> tuple[str, str]:
    paragraphs = []
    for index, paragraph in enumerate(essay["paragraphs"]):
        classes = "essay-paragraph essay-paragraph--opening" if index == 0 else "essay-paragraph"
        paragraphs.append(f'<p class="{classes}">{escape(paragraph)}</p>')

    translations = ""
    if essay["translations"]:
        translation_links = "".join(
            f'<a href="{escape(item["url"])}">{escape(item["label"])}</a>'
            for item in essay["translations"]
        )
        translations = f"""
        <div class="essay-panel">
          <span class="essay-panel__label">Translations</span>
          <div class="essay-links">{translation_links}</div>
        </div>
        """

    thanks = ""
    if essay["thanks"]:
        thanks = f"""
        <div class="essay-panel">
          <span class="essay-panel__label">Acknowledgements</span>
          <p>{escape(essay["thanks"])}</p>
        </div>
        """

    peer_cards = "".join(
        f"""
        <a class="peer-card" href="../{escape(peer['slug'])}/">
          <span>{escape(peer['date_text'] or str(peer['year']))}</span>
          <strong>{escape(peer['title'])}</strong>
        </a>
        """
        for peer in peers
    )

    prev_link = (
        f'<a class="pager-card" href="../{escape(prev_essay["slug"])}/"><span>Previous</span><strong>{escape(prev_essay["title"])}</strong></a>'
        if prev_essay
        else ""
    )
    next_link = (
        f'<a class="pager-card" href="../{escape(next_essay["slug"])}/"><span>Next</span><strong>{escape(next_essay["title"])}</strong></a>'
        if next_essay
        else ""
    )

    prev_url_attr = (
        f'data-prev-url="../{escape(prev_essay["slug"])}/"' if prev_essay else ""
    )
    next_url_attr = (
        f'data-next-url="../{escape(next_essay["slug"])}/"' if next_essay else ""
    )

    body_attrs = f'class="essay-page" data-reading-view {prev_url_attr} {next_url_attr}'.strip()

    return body_attrs, f"""
    <div class="reading-progress" data-reading-progress><span></span></div>
    <header class="site-header site-header--overlay">
      <a class="brand" href="../../">PG / Library</a>
      <nav class="site-nav">
        <a href="../../#chapters">Contents</a>
        <a href="{escape(essay['source_url'])}">Original</a>
      </nav>
    </header>

    <main class="essay-shell">
      <aside class="essay-rail reveal">
        <div class="essay-panel">
          <span class="essay-panel__label">Chapter</span>
          <strong>Chapter {essay['chapter_number']:03d}</strong>
          <p>{escape(essay['date_text'] or str(essay['year']))}</p>
        </div>
        <div class="essay-panel">
          <span class="essay-panel__label">Reading Time</span>
          <strong>{essay['reading_minutes']} minutes</strong>
          <p>{format_number(essay['word_count'])} words</p>
        </div>
        <div class="essay-panel">
          <span class="essay-panel__label">Source</span>
          <a href="{escape(essay['source_url'])}">Open the original essay</a>
        </div>
        {translations}
        {thanks}
      </aside>

      <article class="essay-sheet reveal">
        <div class="essay-sheet__header">
          <span class="eyebrow">Collected Essays of Paul Graham</span>
          <h1>{escape(essay['title'])}</h1>
          <div class="essay-meta">
            <span>{escape(essay['date_text'] or str(essay['year']))}</span>
            <span>{essay['reading_minutes']} min read</span>
            <span>{format_number(essay['word_count'])} words</span>
          </div>
          <blockquote class="pull-quote">
            {escape(essay['pull_quote'])}
          </blockquote>
        </div>
        <div class="essay-content">
          {''.join(paragraphs)}
        </div>
        <div class="essay-pager">
          {prev_link}
          {next_link}
        </div>
      </article>

      <aside class="essay-aside reveal">
        <div class="essay-panel">
          <span class="essay-panel__label">Chapter Focus</span>
          <p>{escape(essay['excerpt'])}</p>
        </div>
        <div class="essay-panel">
          <span class="essay-panel__label">Same-Year Reading</span>
          <div class="peer-list">
            {peer_cards or '<span class="peer-list__empty">No additional essays from this year were surfaced.</span>'}
          </div>
        </div>
      </aside>
    </main>
    """


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def build() -> None:
    payload = load_payload()
    essays = payload["essays"]
    asset_version = datetime.now().strftime("%Y%m%d%H%M%S")

    DIST_DIR.mkdir(parents=True, exist_ok=True)
    DIST_ASSETS_DIR.mkdir(parents=True, exist_ok=True)

    for filename in ("styles.css", "app.js"):
        copy2(ASSETS_DIR / filename, DIST_ASSETS_DIR / filename)

    home = shell(
        page_title="PG Library",
        description="A premium book-style archive of Paul Graham’s essays.",
        body_html=render_home(essays, payload),
        depth=0,
        asset_version=asset_version,
        body_attrs='class="home-page"',
    )
    write_text(DIST_DIR / "index.html", home)

    for index, essay in enumerate(essays):
        prev_essay = essays[index - 1] if index > 0 else None
        next_essay = essays[index + 1] if index + 1 < len(essays) else None
        peers = [item for item in essays if item["year"] == essay["year"] and item["slug"] != essay["slug"]][:4]
        body_attrs, body_html = render_chapter_page(essay, prev_essay, next_essay, peers)
        page = shell(
            page_title=f"{essay['title']} | PG Library",
            description=essay["excerpt"],
            body_html=body_html,
            depth=2,
            asset_version=asset_version,
            body_attrs=body_attrs,
        )
        write_text(DIST_DIR / "essays" / essay["slug"] / "index.html", page)

    write_text(DIST_DIR / "data" / "essays.json", json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    write_text(DIST_DIR / "robots.txt", "User-agent: *\nAllow: /\n")

    site_url = os.environ.get("SITE_URL", "").strip().rstrip("/")
    if site_url:
        urls = [f"{site_url}/"] + [f"{site_url}/essays/{essay['slug']}/" for essay in essays]
        sitemap = "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
        sitemap += "<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">\n"
        sitemap += "\n".join(f"  <url><loc>{escape(url)}</loc></url>" for url in urls)
        sitemap += "\n</urlset>\n"
        write_text(DIST_DIR / "sitemap.xml", sitemap)

    print(f"Built static site in {DIST_DIR}")


if __name__ == "__main__":
    build()
