# SignalFlow — Intelligent Information Pipeline

[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/docker-ready-2496ED.svg?logo=docker)](https://www.docker.com/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-active-brightgreen.svg)]()

> A 24/7 autonomous AI pipeline that scrapes, filters, summarizes, and delivers multi-platform content to your Telegram — powered by a 3-stage specialized model chain.

---

## Architecture

```
Multi-platform Sources          AI Pipeline                   Delivery
┌──────────────┐         ┌──────────────────────┐         ┌──────────────┐
│   Reddit     │──┐      │ ① DeepSeek-chat      │         │  Telegram    │
│   (live)     │  │      │   Batch filter       │         │  Push        │
└──────────────┘  │      │   (spam / noise)      │         └──────────────┘
                  │      └──────────┬───────────┘
┌──────────────┐  │                 ▼                    ┌──────────────┐
│   Twitter/X  │  │      ┌──────────────────────┐        │  Markdown    │
│   (planned)  │──┼─────▶│ ② Claude Sonnet 4.6  │───────▶│  Knowledge   │
└──────────────┘  │      │   Deep summarization  │        │  Base        │
                  │      │   Sentiment + Score    │        └──────────────┘
┌──────────────┐  │      └──────────┬───────────┘
│   Zhihu      │  │                 │
│   (planned)  │──┘                 ▼
└──────────────┘           ┌──────────────────────┐
                           │ ③ Gemini 2.5 Flash   │
                           │   Visual / chart     │
                           │   analysis            │
                           └──────────────────────┘
```

## How SignalFlow Works

Each post passes through a **specialized 3-model pipeline**:

| Stage | Model | Role | Cost |
|-------|-------|------|------|
| **Filter** | DeepSeek-chat | Bulk pass — discards ads, spam, and low-value posts via structured JSON output | Low |
| **Analyze** | Claude Sonnet 4.6 | Deep reading — generates Chinese summaries, sentiment labels (bullish/bearish/neutral), importance score (1–10), category tags, and keywords | Medium |
| **See** | Gemini 2.5 Flash | Optional screenshot analysis for charts, memes, and visual trends | Low |

**Quality control:** MD5-based deduplication with a 10,000-item rolling window ensures you never see the same post twice.

## Features

- **Multi-source scraping** — Reddit live (9 subreddits covering crypto, stocks, AI/ML, world news); Twitter, Zhihu, Xiaohongshu, Bilibili, YouTube planned
- **Scheduled delivery** — Morning briefing (08:00) and evening briefing (20:00) Beijing time
- **Urgent alerts** — Every 30 minutes for high-importance (≥8) crypto and investment signals
- **On-demand commands** — `/today`, `/urgent`, `/sources` via Telegram Bot
- **Full-text search** — ripgrep-powered knowledge base over all archived briefings
- **Docker-native** — 3 services (bot, scheduler, Playwright browser) in one `docker compose up`

## Tech Stack

| Layer | Technology |
|-------|------------|
| Scraping | Playwright (async) + `playwright-stealth` |
| AI SDKs | Anthropic SDK, OpenAI SDK (DeepSeek), Google GenAI SDK |
| Bot | `python-telegram-bot` v21.10+ |
| Scheduling | APScheduler (AsyncIOScheduler) |
| Storage | Markdown + YAML frontmatter + ripgrep |
| Deployment | Docker Compose (3 services) |

## Quick Start

```bash
# 1. Clone
git clone https://github.com/carloshuangspec/SignalFlow.git
cd SignalFlow

# 2. Configure
cp .env.example .env
# Fill in: CLAUDE_API_KEY, DEEPSEEK_API_KEY, GEMINI_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

# 3. Launch
docker compose up -d

# 4. Verify — message your bot on Telegram:
#    /start   → welcome message
#    /today   → manual briefing trigger
```

## Project Structure

```
SignalFlow/
├── main.py                  # Entry point (bot | scheduler | run-once | all)
├── docker-compose.yml       # 3-service orchestration
├── Dockerfile               # python:3.12-slim base
├── requirements.txt         # Python dependencies
│
├── scrapers/
│   ├── base_scraper.py      # Playwright + stealth abstract base class
│   └── reddit_scraper.py    # old.reddit.com top-posts parser
│
├── pipeline/
│   ├── summarizer.py        # 3-model AI pipeline engine
│   └── formatter.py         # Telegram HTML + Markdown output
│
├── bot/
│   └── telegram_bot.py      # Command handler + push interface
│
├── scheduler/
│   └── jobs.py              # Cron jobs (briefings + urgent alerts)
│
├── knowledge/
│   └── markdown_store.py    # File-based knowledge base with full-text search
│
└── dashboard/
    └── index.html           # Web dashboard (static preview)
```

## Roadmap

| Phase | Items |
|-------|-------|
| **Phase 2** | Twitter/X, Zhihu, Xiaohongshu, Bilibili, YouTube scrapers |
| **Phase 3** | Vector search knowledge base (embeddings + RAG) |
| **Phase 4** | Crypto & stock market real-time alerting |
| **Phase 5** | Full web dashboard with data visualization |
---

<p align="center">
  <sub>Designed for 24/7 autonomous operation</sub>
</p>
