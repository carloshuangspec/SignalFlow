"""
AI 摘要管线 — 多模型路由、筛选、摘要、去重。
"""
import os
import json
import hashlib
import asyncio
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Optional

from anthropic import AsyncAnthropic
from openai import AsyncOpenAI
from google import genai


@dataclass
class BriefItem:
    """简报条目"""
    title: str
    summary_cn: str           # 2 句中文摘要
    sentiment: str            # 看涨/看跌/中性/信息
    importance: int           # 1-10
    source_platform: str
    source_url: str
    source_name: str          # subreddit / 作者
    category: str = ""        # 自动分类
    keywords: list[str] = field(default_factory=list)


class AISummarizer:
    """多模型 AI 摘要引擎"""

    def __init__(self):
        self.claude = AsyncAnthropic(api_key=os.getenv("CLAUDE_API_KEY"))
        self.deepseek = AsyncOpenAI(
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url="https://api.deepseek.com/v1",
        )
        self.gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

        self.primary_model = os.getenv("PRIMARY_MODEL", "claude-sonnet-4-6")
        self.batch_model = os.getenv("BATCH_MODEL", "deepseek-chat")
        self.vision_model = os.getenv("VISION_MODEL", "gemini-2.5-flash")

        self._seen_hashes: set[str] = set()

    # ─── 主入口 ───

    async def generate_briefing(
        self, posts: list, categories: list[str] | None = None
    ) -> list[BriefItem]:
        """主流程：原始帖子 → AI 筛选摘要 → 结构化简报"""
        if not posts:
            return []

        # Step 1: 批量初筛（DeepSeek，便宜量大）
        filtered = await self._batch_filter(posts)

        # Step 2: 精摘要（Claude，质量高）
        items = await self._deep_summarize(filtered)

        # Step 3: 去重
        items = self._deduplicate(items)

        # Step 4: 按重要度排序
        items.sort(key=lambda x: x.importance, reverse=True)

        return items

    # ─── Step 1: 批量初筛 ───

    async def _batch_filter(self, posts: list) -> list:
        """用 DeepSeek 批量筛选，过滤低价值帖子"""
        posts_text = self._format_posts_for_ai(posts)
        if not posts_text:
            return posts[:20]

        prompt = f"""你是一个信息筛选助手。以下是来自多个平台的帖子列表。

任务：
1. 过滤掉广告、垃圾信息、纯情绪发泄无实质内容的帖子
2. 保留有信息量、有洞察、有争议、或对留学生/投资者/技术学习者有价值的帖子
3. 返回保留帖子的 ID 列表（从 0 开始编号）

=== 帖子列表 ===
{posts_text}

返回 JSON 格式：
{{"keep_ids": [0, 3, 5, ...], "reason": "一句话说明筛选逻辑"}}"""

        try:
            resp = await self.deepseek.chat.completions.create(
                model=self.batch_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
                temperature=0.1,
            )
            data = json.loads(resp.choices[0].message.content)
            keep_ids = set(data.get("keep_ids", []))
            return [p for i, p in enumerate(posts) if i in keep_ids]
        except Exception as e:
            print(f"[Summarizer] Batch filter failed: {e}")
            return posts[:20]  # fallback: 取前 20

    # ─── Step 2: 精摘要 ───

    async def _deep_summarize(self, posts: list) -> list[BriefItem]:
        """用 Claude 对筛选后的帖子做深度摘要"""
        if not posts:
            return []

        posts_text = self._format_posts_for_ai(posts)

        prompt = f"""你是 Carlos 的私人 AI 信息助理。阅读以下帖子，为每条生成摘要。

对每条帖子返回：
- summary_cn: 2 句中文摘要，抓住核心信息
- sentiment: "看涨" / "看跌" / "中性" / "信息"（非金融内容用"信息"）
- importance: 1-10 整数（对留学生/技术学习者/投资者的重要性）
- category: 一级分类（Crypto/Tech/AI/投资/留学/新闻/其他）
- keywords: 2-3 个中文关键词

=== 帖子列表 ===
{posts_text}

返回纯 JSON 数组（不要 markdown code block）：
[{{"id": 0, "summary_cn": "...", "sentiment": "...", "importance": 7, "category": "...", "keywords": ["...", "..."]}}, ...]"""

        try:
            resp = await self.claude.messages.create(
                model=self.primary_model,
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}],
            )
            text = resp.content[0].text
            data = json.loads(self._extract_json(text))

            items = []
            for entry in data:
                idx = entry.get("id", 0)
                if idx < len(posts):
                    post = posts[idx]
                    items.append(BriefItem(
                        title=post.title if hasattr(post, 'title') else entry.get("title", ""),
                        summary_cn=entry.get("summary_cn", ""),
                        sentiment=entry.get("sentiment", "信息"),
                        importance=min(max(entry.get("importance", 5), 1), 10),
                        source_platform=post.platform if hasattr(post, 'platform') else "",
                        source_url=post.url if hasattr(post, 'url') else "",
                        source_name=post.metadata.get("subreddit", "") if hasattr(post, 'metadata') else "",
                        category=entry.get("category", "其他"),
                        keywords=entry.get("keywords", []),
                    ))
            return items
        except Exception as e:
            print(f"[Summarizer] Deep summarize failed: {e}")
            return []

    # ─── Step 3: 去重 ───

    def _deduplicate(self, items: list[BriefItem]) -> list[BriefItem]:
        unique = []
        for item in items:
            h = hashlib.md5(item.title.encode()).hexdigest()
            if h not in self._seen_hashes:
                self._seen_hashes.add(h)
                unique.append(item)
        # 限制 seen set 大小
        if len(self._seen_hashes) > 10000:
            self._seen_hashes.clear()
        return unique

    # ─── 视觉分析（Gemini） ───

    async def analyze_screenshot(self, screenshot_path: str) -> str:
        """用 Gemini 分析截图，提取视觉信息（图表、meme、排版趋势等）"""
        try:
            img = await asyncio.to_thread(
                self.gemini_client.files.upload, file=screenshot_path
            )
            resp = self.gemini_client.models.generate_content(
                model=self.vision_model,
                contents=[
                    "你是一个信息分析师。这张截图来自社交媒体/论坛。"
                    "描述页面中的关键视觉信息：有什么重要的图表、趋势、meme、或值得注意的讨论？"
                    "用中文回答，控制在 3-5 句。",
                    img,
                ],
            )
            return resp.text
        except Exception as e:
            print(f"[Summarizer] Screenshot analysis failed: {e}")
            return ""

    # ─── 工具方法 ───

    def _format_posts_for_ai(self, posts: list) -> str:
        lines = []
        for i, p in enumerate(posts):
            platform = getattr(p, "platform", "")
            title = getattr(p, "title", "")
            content = getattr(p, "content", "")
            score = getattr(p, "score", 0)
            comments = getattr(p, "comments_count", 0)
            source = getattr(p, "metadata", {}).get("subreddit", "") if hasattr(p, "metadata") else ""

            lines.append(
                f"[{i}] [{platform}] {source} | {title}\n"
                f"    Score:{score} Comments:{comments}\n"
                f"    {content[:300]}"
            )
        return "\n\n".join(lines)

    @staticmethod
    def _extract_json(text: str) -> str:
        """从 AI 响应中提取 JSON 部分"""
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            lines = [l for l in lines if not l.startswith("```")]
            text = "\n".join(lines)
        # 找第一个 [ 到最后一个 ]
        start = text.find("[")
        end = text.rfind("]")
        if start >= 0 and end > start:
            return text[start:end + 1]
        return text
