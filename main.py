"""
AI_OS 主入口 — 启动所有服务。
用法: python main.py [bot|scheduler|all]
"""
import sys
import asyncio
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("ai_os")


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"

    if mode == "bot":
        from bot.telegram_bot import main as bot_main
        bot_main()
    elif mode == "scheduler":
        from scheduler.jobs import start_scheduler
        start_scheduler()
        try:
            asyncio.get_event_loop().run_forever()
        except KeyboardInterrupt:
            logger.info("Scheduler stopped")
    elif mode == "run-once":
        # 手动跑一次简报，输出到终端
        from scheduler.jobs import run_briefing
        from pipeline.formatter import format_telegram_html
        items = asyncio.run(run_briefing())
        print(format_telegram_html(items))
    else:
        # 启动全部
        import threading
        from bot.telegram_bot import main as bot_main
        from scheduler.jobs import start_scheduler

        logger.info("Starting AI_OS (all services)...")
        t = threading.Thread(target=bot_main, daemon=True)
        t.start()
        start_scheduler()
        try:
            asyncio.get_event_loop().run_forever()
        except KeyboardInterrupt:
            logger.info("AI_OS stopped")


if __name__ == "__main__":
    main()
