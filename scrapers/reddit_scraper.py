"""
Reddit 爬虫 — old.reddit.com 文本提取 + 截图。
"""
import re
from datetime import datetime, timezone

from .base_scraper import BaseScraper, ScrapedPost


class RedditScraper(BaseScraper):
    platform = "reddit"
    base_url = "https://old.reddit.com"

    # 默认监控的 subreddits
    DEFAULT_SUBREDDITS = [
        "CryptoCurrency",
        "wallstreetbets",
        "stocks",
        "MachineLearning",
        "ChatGPT",
        "LocalLLaMA",
        "ArtificialInteligence",
        "technology",
        "worldnews",
    ]

    async def scrape(
        self, subreddits: list[str] | None = None, limit: int = 30
    ) -> list[ScrapedPost]:
        subreddits = subreddits or self.DEFAULT_SUBREDDITS
        all_posts: list[ScrapedPost] = []

        browser, context = await self._launch_browser()
        try:
            for sub in subreddits:
                posts = await self._scrape_subreddit(context, sub, limit)
                all_posts.extend(posts)
        finally:
            await browser.close()

        return all_posts

    async def _scrape_subreddit(
        self, context, subreddit: str, limit: int
    ) -> list[ScrapedPost]:
        page = await context.new_page()
        await self._setup_page(page)

        url = f"{self.base_url}/r/{subreddit}/top/?sort=top&t=day&limit={limit}"
        posts: list[ScrapedPost] = []

        try:
            await page.goto(url, wait_until="networkidle", timeout=30000)
            await self._human_scroll(page, times=2)

            screenshot_path = await self._screenshot(page, f"reddit_{subreddit}")

            entries = await page.query_selector_all("div.thing")
            for entry in entries[:limit]:
                try:
                    post = await self._parse_entry(entry, subreddit, screenshot_path)
                    if post:
                        posts.append(post)
                except Exception:
                    continue

        except Exception as e:
            print(f"[Reddit] Error scraping r/{subreddit}: {e}")
        finally:
            await page.close()

        return posts

    async def _parse_entry(self, entry, subreddit: str, screenshot: str) -> ScrapedPost | None:
        # 标题
        title_el = await entry.query_selector("a.title")
        if not title_el:
            return None
        title = self._clean_text(await title_el.inner_text())

        # URL
        href = await title_el.get_attribute("href")
        url = href if href.startswith("http") else f"{self.base_url}{href}"

        # 分数
        score_str = await entry.get_attribute("data-score")
        score = int(score_str) if score_str else 0

        # 评论数
        comments_el = await entry.query_selector("a.comments")
        comments_text = await comments_el.inner_text() if comments_el else "0"
        comments_match = re.search(r"(\d+)", comments_text)
        comments_count = int(comments_match.group(1)) if comments_match else 0

        # 作者
        author_el = await entry.query_selector("a.author")
        author = self._clean_text(await author_el.inner_text()) if author_el else "unknown"

        # 时间
        time_el = await entry.query_selector("time")
        timestamp = await time_el.get_attribute("datetime") if time_el else None

        # 内容预览（selftext）
        content = ""
        expand_el = await entry.query_selector("div.expando div.md")
        if expand_el:
            content = self._clean_text(await expand_el.inner_text())

        return ScrapedPost(
            platform="reddit",
            title=title,
            content=content[:2000],
            url=url,
            author=author,
            score=score,
            comments_count=comments_count,
            timestamp=timestamp,
            screenshot_path=screenshot,
            metadata={"subreddit": subreddit},
        )
