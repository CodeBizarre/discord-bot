import aiohttp

from discord.ext import commands
from discord.ext.commands import Context

from discordbot.core.discord_bot import DiscordBot

VERSION = "1.1b3"


class Inspirobot(commands.Cog):
    """Get inspirational images from the Inspirobot."""

    def __init__(self, bot: DiscordBot):
        self.bot = bot
        self.name = "inspirobot"
        self.version = VERSION

    @commands.command(aliases=["ib", "inspire"])
    async def inspirobot(self, ctx: Context):
        """Get an image from the inspirobot."""
        async with aiohttp.ClientSession() as session:
            response = await session.get("http://inspirobot.me/api?generate=true")
            url = await response.text()

        await ctx.send(url)


def setup(bot):
    bot.add_cog(Inspirobot(bot))
