"""Optional Discord client of the same FastAPI service (no Discord logic in core).

Requires: pip install '.[discord]' and DISCORD_BOT_TOKEN in the environment.
Run the API and then: python -m scarascope.discord_bot
"""
import asyncio
import os

import httpx
from dotenv import load_dotenv


def main() -> None:
    load_dotenv()
    try:
        import discord
        from discord.ext import commands
    except ImportError as exc:
        raise SystemExit("Install optional dependencies: pip install '.[discord]'") from exc

    token = os.getenv("DISCORD_BOT_TOKEN", "")
    if not token:
        raise SystemExit("Set DISCORD_BOT_TOKEN in .env (never commit it).")
    api_base = os.getenv("SCARASCOPE_API_URL", "http://127.0.0.1:8000").rstrip("/")
    api_key = os.getenv("SCARASCOPE_API_KEY", "")
    intents = discord.Intents.default()
    intents.message_content = True  # Enable Message Content Intent in the Discord Developer Portal.
    bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

    @bot.command(name="scope")
    async def scope(ctx, ticker: str = "DEMO"):
        """!scope DEMO or !scope MSFT"""
        async with ctx.typing():
            try:
                async with httpx.AsyncClient(timeout=65) as client:
                    response = await client.post(f"{api_base}/api/research", json={"ticker": ticker}, headers={"X-API-Key": api_key})
                    response.raise_for_status()
                    data = response.json()
                rows = data.get("financials", [])
                latest = rows[0] if rows else {}
                title = f"{data['company']} ({data['ticker']})"
                label = "FICTIONAL DEMO" if data["data_kind"] == "synthetic_demo" else "SEC FINANCIAL FACTS"
                embed = discord.Embed(title=title, description=data["summary"][:3500], color=0x157F64)
                embed.add_field(name="Data", value=label)
                embed.add_field(name="Latest period", value=latest.get("period_end", "Unavailable"))
                embed.add_field(name="Model", value=data["llm"]["provider"])
                if data["data_kind"] == "sec_live":
                    embed.add_field(name="Source", value=data["data_source"], inline=False)
                await ctx.reply(embed=embed, mention_author=False)
            except (httpx.HTTPError, KeyError, ValueError) as exc:
                await ctx.reply(f"ScaraScope request failed. Check API configuration. ({type(exc).__name__})", mention_author=False)

    @bot.command(name="scopehelp")
    async def scopehelp(ctx):
        await ctx.reply("ScaraScope: `!scope DEMO` (fictional sample) or `!scope MSFT` (live SEC, requires SEC_USER_AGENT).", mention_author=False)

    bot.run(token)


if __name__ == "__main__":
    main()
