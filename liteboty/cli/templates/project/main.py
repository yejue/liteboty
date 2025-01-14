from liteboty.core import Bot
import asyncio

if __name__ == "__main__":
    bot = Bot()
    try:
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        # wait for the bot to terminate
        asyncio.run(bot.stop())