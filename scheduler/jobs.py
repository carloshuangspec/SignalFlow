"""
定时任务调度器 — 所有 cron 任务定义。
"""
import os
import asyncio
import logging
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from scrapers.reddit_scraper import RedditScraper
from pipeline.summarizer import AISummarizer, BriefItem
from pipeline.formatter import format_markdown_digest
from bot.telegram_bot import push_briefing, push_urgent
from knowledge.markdown_store import MarkdownStore

logger = logging.getLogger("scheduler")

scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")
summarizer = AISummarizer()
store = MarkdownStore()


async def run_briefing() -> list[BriefItem]:
    """执行一次完整的抓取→摘要流程"""
    logger.info("Starting briefing run...")

    # 1. 抓取 Reddit
    scraper = RedditScraper()
    try:
        posts = await scraper.scrape(limit=20)
        logger.info(f"Scraped {len(posts)} Reddit posts")
    except Exception as e:
        logger.error(f"Scraper failed: {e}")
        posts = []

    # 2. AI 摘要
    items = await summarizer.generate_briefing(posts)

    # 3. 存入知识库
    if items:
        md = format_markdown_digest(items)
        store.save_daily_briefing(md)

    logger.info(f"Briefing complete: {len(items)} items")
    return items


async def morning_briefing():
    """早上 8 点简报"""
    items = await run_briefing()
    await push_briefing(items, kind="morning")


async def evening_briefing():
    """晚上 8 点简报"""
    items = await run_briefing()
    await push_briefing(items, kind="evening")


async def market_check():
    """每 30 分钟检查市场异常（Phase 2 完整实现）"""
    items = await run_briefing()
    urgent = [i for i in items if i.importance >= 8 and i.category in ("Crypto", "投资")]
    if urgent:
        await push_urgent(items)


def start_scheduler():
    """启动所有定时任务"""
    # 早间简报 08:00
    scheduler.add_job(
        morning_briefing,
        CronTrigger(hour=8, minute=0),
        id="morning_briefing",
        replace_existing=True,
    )
    # 晚间简报 20:00
    scheduler.add_job(
        evening_briefing,
        CronTrigger(hour=20, minute=0),
        id="evening_briefing",
        replace_existing=True,
    )
    # 市场巡检 每 30 分钟（交易时段）
    scheduler.add_job(
        market_check,
        CronTrigger(minute="*/30"),
        id="market_check",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("Scheduler started: morning=08:00, evening=20:00, market=*/30")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    start_scheduler()
    try:
        asyncio.get_event_loop().run_forever()
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
