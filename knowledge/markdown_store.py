"""
知识库 MVP — Markdown 文件存储 + 索引。
"""
import os
import re
from pathlib import Path
from datetime import datetime, timezone


class MarkdownStore:
    """Markdown 知识库"""

    def __init__(self, base_dir: str | None = None):
        self.base_dir = Path(base_dir or os.getenv("KNOWLEDGE_DIR", "/data/ai_os/knowledge"))
        self.base_dir.mkdir(parents=True, exist_ok=True)

        # 子目录
        self.briefings_dir = self.base_dir / "briefings"
        self.articles_dir = self.base_dir / "articles"
        self.notes_dir = self.base_dir / "notes"
        for d in [self.briefings_dir, self.articles_dir, self.notes_dir]:
            d.mkdir(exist_ok=True)

    def save_daily_briefing(self, markdown: str) -> str:
        """保存每日简报"""
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        path = self.briefings_dir / f"{date_str}.md"
        path.write_text(markdown, encoding="utf-8")
        return str(path)

    def save_article(self, title: str, content: str, source_url: str = "", tags: list[str] | None = None) -> str:
        """保存单篇文章/帖子"""
        slug = re.sub(r"[^\w]+", "-", title.lower())[:80]
        ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        filename = f"{ts}_{slug}.md"
        path = self.articles_dir / filename

        tag_line = " ".join(f"#{t}" for t in (tags or []))
        text = f"""---
title: "{title}"
source: "{source_url}"
date: {datetime.now(timezone.utc).isoformat()}
tags: [{", ".join(tags or [])}]
---

# {title}

{tag_line}

{content}
"""
        path.write_text(text, encoding="utf-8")
        return str(path)

    def save_note(self, title: str, content: str) -> str:
        """保存个人笔记"""
        slug = re.sub(r"[^\w]+", "-", title.lower())[:50]
        ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        path = self.notes_dir / f"{ts}_{slug}.md"

        path.write_text(f"# {title}\n\n{content}", encoding="utf-8")
        return str(path)

    def list_recent_briefings(self, days: int = 7) -> list[str]:
        """列出最近 N 天的简报路径"""
        files = sorted(self.briefings_dir.glob("*.md"), reverse=True)
        return [str(f) for f in files[:days]]

    def search(self, keyword: str) -> list[str]:
        """用 ripgrep 全文搜索（需在 VPS 上运行）"""
        import subprocess
        try:
            result = subprocess.run(
                ["rg", "-l", "--ignore-case", keyword, str(self.base_dir)],
                capture_output=True, text=True, timeout=10,
            )
            return result.stdout.strip().split("\n") if result.stdout else []
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return list(self.base_dir.rglob("*.md"))
