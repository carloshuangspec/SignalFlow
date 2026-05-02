"""
Telegram Bot — AI_OS 推送中枢。
命令: /today /urgent /sources /pause /resume /help
"""
import os
import asyncio
import logging

from telegram import Update, BotCommand
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.constants import ParseMode

from pipeline.summarizer import AISummarizer, BriefItem
from pipeline.formatter import format_telegram_html

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("telegram_bot")

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

summarizer = AISummarizer()

# ─── 命令处理 ───

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_html(
        "<b>🤖 AI_OS 已上线</b>\n\n"
        "我是你的私人 AI 信息助理。\n\n"
        "<b>命令列表：</b>\n"
        "/today — 查看今日简报\n"
        "/urgent — 查看高优先级预警\n"
        "/sources — 查看信息源状态\n"
        "/pause — 暂停推送\n"
        "/resume — 恢复推送\n"
        "/help — 显示此帮助"
    )


async def today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """手动触发今日简报"""
    await update.message.reply_text("🔄 正在生成今日简报，请稍候...")
    try:
        from scheduler.jobs import run_briefing
        items = await run_briefing()
        text = format_telegram_html(items, "📋 今日简报")
        await update.message.reply_html(text)
    except Exception as e:
        await update.message.reply_text(f"❌ 生成失败: {e}")


async def urgent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """只看高重要度条目"""
    await update.message.reply_text("🔄 正在筛选高优先级信息...")
    try:
        from scheduler.jobs import run_briefing
        items = await run_briefing()
        urgent_items = [i for i in items if i.importance >= 7]
        text = format_telegram_html(urgent_items, "🚨 高优先级预警")
        await update.message.reply_html(text)
    except Exception as e:
        await update.message.reply_text(f"❌ 生成失败: {e}")


async def sources(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """查看信息源状态"""
    await update.message.reply_html(
        "<b>📡 信息源状态</b>\n\n"
        "🟢 Reddit — 正常 (r/CryptoCurrency, r/wallstreetbets, ...)\n"
        "⚪ Twitter/X — Phase 2 接入\n"
        "⚪ 知乎 — Phase 2 接入\n"
        "⚪ 小红书 — Phase 2 接入\n"
        "⚪ YouTube — Phase 2 接入\n"
        "⚪ B站 — Phase 2 接入\n\n"
        "<i>推送时间: 每日 08:00 / 20:00 (北京时间)</i>"
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)


# ─── 推送方法（供调度器调用）───

async def push_briefing(items: list[BriefItem], kind: str = "morning"):
    """向用户推送简报"""
    if not TOKEN or not CHAT_ID:
        logger.error("TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set")
        return

    app = Application.builder().token(TOKEN).build()
    title = "☀️ 早安简报" if kind == "morning" else "🌙 晚间简报"
    text = format_telegram_html(items, title)

    try:
        await app.bot.send_message(
            chat_id=CHAT_ID,
            text=text,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
        )
        logger.info(f"Pushed {kind} briefing, {len(items)} items")
    except Exception as e:
        logger.error(f"Push failed: {e}")


async def push_urgent(items: list[BriefItem]):
    """紧急推送高重要度信息"""
    urgent_items = [i for i in items if i.importance >= 8]
    if not urgent_items:
        return

    app = Application.builder().token(TOKEN).build()
    text = format_telegram_html(urgent_items, "🚨 重要预警")

    try:
        await app.bot.send_message(
            chat_id=CHAT_ID,
            text=text,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
        )
        logger.info(f"Pushed urgent alert, {len(urgent_items)} items")
    except Exception as e:
        logger.error(f"Urgent push failed: {e}")


# ─── 主入口 ───

def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("today", today))
    app.add_handler(CommandHandler("urgent", urgent))
    app.add_handler(CommandHandler("sources", sources))
    app.add_handler(CommandHandler("help", help_cmd))

    logger.info("Telegram Bot started")
    app.run_polling()


if __name__ == "__main__":
    main()
