# PG Library

A static, book-style reading experience for Paul Graham's essays.

## What it does

- Scrapes the live essay index at `https://paulgraham.com/articles.html`
- Fetches each essay and normalizes it into chapter data
- Generates a polished static site in `dist/`
- Ships with zero runtime dependencies and simple deployment config for Vercel or Netlify

## Commands

```bash
pip3 install -r requirements.txt
npm run scrape
npm run build
npm run refresh
npm run serve
```

## Project structure

- `scripts/scrape_pg.py`: fetches and normalizes the essay corpus
- `scripts/build_site.py`: renders the static book site
- `src/assets/styles.css`: design system and page styling
- `src/assets/app.js`: search, filters, reveal motion, and reading progress
- `requirements.txt`: Python dependencies for local and deployment builds
- `data/essays.json`: generated content dataset
- `dist/`: generated site output

## Notes

- The older repo `https://github.com/avyfain/pg-essays` was audited before reuse and only used as a reference for extraction heuristics.
- This project republishes essay text. For a public deployment, confirm you have the right to host the full corpus.
