"""
Playwright 爬虫基类 — 视觉截图 + 内容提取。
所有平台爬虫继承此类，统一反检测、滚动、截图逻辑。
"""
import os
import random
import time
import asyncio
from pathlib import Path
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Optional

from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from playwright_stealth import stealth_async


@dataclass
class ScrapedPost:
    """爬取的帖子数据结构"""
    platform: str
    title: str
    content: str
    url: str
    author: str
    score: int = 0
    comments_count: int = 0
    timestamp: Optional[str] = None
    screenshot_path: Optional[str] = None
    metadata: dict = field(default_factory=dict)


class BaseScraper:
    """Playwright 爬虫基类"""

    platform: str = "base"
    base_url: str = ""

    def __init__(self, data_dir: str = "/data/ai_os"):
        self.data_dir = Path(data_dir)
        self.screenshots_dir = self.data_dir / "screenshots" / self.platform
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)

        self.viewport_width = int(os.getenv("VIEWPORT_WIDTH", "1280"))
        self.viewport_height = int(os.getenv("VIEWPORT_HEIGHT", "900"))
        self.crawl_interval = float(os.getenv("CRAWL_INTERVAL", "3"))

        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None

    async def _launch_browser(self, ws_endpoint: Optional[str] = None) -> tuple[Browser, BrowserContext]:
        """启动浏览器，优先连接已有 Playwright 服务"""
        pw = await async_playwright().start()
        if ws_endpoint:
            browser = await pw.chromium.connect_over_cdp(ws_endpoint)
        else:
            browser = await pw.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                ],
            )

        context = await browser.new_context(
            viewport={"width": self.viewport_width, "height": self.viewport_height},
            user_agent=self._random_ua(),
            locale="en-US",
            timezone_id="Asia/Tokyo",
        )
        return browser, context

    async def _setup_page(self, page: Page) -> None:
        """给页面装 stealth 插件 + 反检测"""
        await stealth_async(page)
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => false });
            Object.defineProperty(navigator, 'plugins', { get: () => [1,2,3,4,5] });
            Object.defineProperty(navigator, 'languages', { get: () => ['en-US','en'] });
            window.chrome = { runtime: {} };
        """)

    @staticmethod
    def _random_ua() -> str:
        ua_list = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0",
        ]
        return random.choice(ua_list)

    async def _human_scroll(self, page: Page, times: int = 3) -> None:
        """模拟人类滚动"""
        for _ in range(times):
            scroll = random.randint(400, 800)
            await page.evaluate(f"window.scrollBy(0, {scroll})")
            await asyncio.sleep(random.uniform(1.0, 2.5))

    async def _screenshot(self, page: Page, name: str) -> str:
        """截取整页截图，返回文件路径"""
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"{name}_{ts}.png"
        path = self.screenshots_dir / filename
        await page.screenshot(path=str(path), full_page=True)
        return str(path)

    async def scrape(self) -> list[ScrapedPost]:
        """子类必须实现此方法"""
        raise NotImplementedError

    @staticmethod
    def _clean_text(text: str) -> str:
        """清理文本：去多余空白、控制字符"""
        import re
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
        return text.strip()
