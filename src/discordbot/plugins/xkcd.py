import asyncio

import xkcd as comics

from discord import Embed
from discord.ext import commands
from discord.ext.commands import Context

from discordbot.core.discord_bot import DiscordBot

# Uncomment the following line to fly
# import antigravity

VERSION = "1.3b1"


class Xkcd(commands.Cog):
    """A plugin to retrieve XKCD comics."""

    def __init__(self, bot: DiscordBot):
        self.bot = bot
        self.name = "xkcd"
        self.version = VERSION

    async def get_comic(self, comic, number=None) -> Embed:
        """Helper function to get comics"""
        case = {
            "latest": lambda: comics.getLatestComic(),
            "random": lambda: comics.getRandomComic(),
            "number": lambda: comics.getComic(number),
        }

        function = case.get(comic, None)
        exc = self.bot.loop.run_in_executor(None, function)

        while not exc.done():
            await asyncio.sleep(0.1)
        result = exc.result()

        try:
            image_link = result.getImageLink()
            title = result.getAsciiTitle().decode("ascii")
            alt_text = result.getAsciiAltText().decode("ascii")
            number = result.number

            embed = Embed(title=title, url=f"https://xkcd.com/{number}", color=0x96A8C8)
            embed.add_field(name=str(number), value=alt_text)
            embed.set_image(url=image_link)

            return embed
        except AttributeError as error:
            embed = Embed(title="Error", color=0xFF0000)
            embed.add_field(name="Details", value=str(error))
            return embed

    @commands.group()
    async def xkcd(self, ctx: Context):
        """Get XKCD comics!

        Running the command without arguments will display the latest comic.
        """
        if ctx.invoked_subcommand is None:
            comic = await self.get_comic("latest")
            await ctx.send(embed=comic)

    @xkcd.command(name="random")
    async def xkcd_random(self, ctx: Context):
        """Get a random xkcd comic."""
        comic = await self.get_comic("random")
        await ctx.send(embed=comic)

    @xkcd.command(name="number")
    async def xkcd_number(self, ctx: Context, number: int):
        """Get xkcd comic <number>."""
        comic = await self.get_comic("number", number)
        await ctx.send(embed=comic)

    @xkcd.command(name="import")
    async def xkcd_import(self, ctx: Context, module: str):
        """Try antigravity!"""
        # TODO: Other modules for funsies
        if module == "antigravity":
            comic = await self.get_comic("number", 353)
            await ctx.send(embed=comic)
        else:
            await ctx.send(f"Module {module} imported.")


def setup(bot):
    bot.add_cog(Xkcd(bot))
