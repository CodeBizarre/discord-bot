import asyncio

import xkcd
from discord.ext import commands
from discord.ext.commands import Context

# Uncomment the following line to fly
#import antigravity

VERSION = "1.0b3"

class XKCD(commands.Cog):
    """A plugin to retrieve XKCD comics."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.name = "xkcd"

    # Helper function for getting comics
    async def get_comic(self, comic, number = None):
        case = {
            "latest": lambda: xkcd.getLatestComic(),
            "random": lambda: xkcd.getRandomComic(),
            "number": lambda: xkcd.getComic(number)
        }

        function = case.get(comic, None)
        exc = self.bot.loop.run_in_executor(None, function)

        while not exc.done():
            await asyncio.sleep(0.1)
        exc = exc.result()

        try:
            link = exc.getImageLink()
            title = exc.getAsciiTitle().decode("ascii")
            alt_text = exc.getAsciiAltText().decode("ascii")
            number = exc.number
            return f"{number} - {link}\n**{title}**\n**Alt:** {alt_text}"
        except AttributeError as error:
            return f"There was a problem: {error}"

    # XKCD command
    @commands.group()
    async def xkcd(self, ctx: Context):
        """Get XKCD comics!

        Running the command without arguments will display the latest comic.
        """
        if ctx.invoked_subcommand is None:
            comic = await self.get_comic("latest")
            await ctx.send(comic)

    @xkcd.command(name="random")
    async def xkcd_random(self, ctx: Context):
        """Get a random xkcd comic."""
        comic = await self.get_comic("random")
        await ctx.send(comic)

    @xkcd.command(name="number")
    async def xkcd_number(self, ctx: Context, number: int):
        """Get a specific xkcd comic."""
        comic = await self.get_comic("number", number)
        await ctx.send(comic)

    @xkcd.command(name="import")
    async def xkcd_import(self, ctx: Context, module: str):
        """Relevant, because Python."""
        # TODO: Other modules for funsies
        if module == "antigravity":
            comic = await self.get_comic("number", 353)
            await ctx.send(comic)
        else:
            await ctx.send(f"Module {module} imported.")

def setup(bot):
    bot.add_cog(XKCD(bot))
