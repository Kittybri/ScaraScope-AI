"""Backward-compatible launch command: python -m scarascope.discord_bot.

The actual Discord implementation lives in adapters/discord/bot.py.
"""
from .adapters.discord.bot import main


if __name__ == "__main__":
    main()
