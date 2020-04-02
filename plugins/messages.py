import asyncio
import json

from main import get_account
from helpers import pretty_datetime
from discord import TextChannel, Member, Message, Embed
from discord import HTTPException
from discord.ext import commands
from discord.ext.commands import Context

VERSION = "2.0b1"

# Get the config file to grab the command prefix
prefix = None

try:
    with open("config/config.json") as cfg:
        prefix = json.load(cfg)["Prefix"]
except Exception as error:
    print(f"Error loading prefix from configuration file.\n    - {error}")

def msg_op_or_level(required=10):
    """See if the user is the OP of the message, or high enough level otherwise."""
    async def check(ctx: Context):
        uid = str(ctx.message.author.id)
        loop = ctx.bot.loop

        if ctx.invoked_with == "help":
            ctx.message.content = ""
            return True

        args = ctx.message.content.split(" ")

        exc = asyncio.run_coroutine_threadsafe(
            ctx.fetch_message(args[1]),
            loop
        )

        while not exc.done():
            await asyncio.sleep(0.1)

        try:
            target = exc.result()
        except HTTPException:
            return False

        tid = str(target.author.id)

        if uid == tid:
            return True
        else:
            try:
                user_level = get_account(ctx.guild, ctx.message.author)
            except KeyError as e:
                await ctx.send(f"KeyError: {e}")
                return False
            else:
                return user_level >= required

    return commands.check(check)

class Messages(commands.Cog):
    """Message management plugin.

    Allows cross-posting and moving of messages.
    """
    def __init__(self, bot):
        self.bot = bot
        self.name = "messages"

    @commands.command(aliases=["xpost", "x-post"])
    @msg_op_or_level(5)
    async def crosspost(self, ctx: Context, message: Message, target: TextChannel):
        """Cross-post a message to another channel."""
        embed = Embed(
            title=f"X-Post from #{ctx.channel.name}",
            url=message.jump_url,
            color=0xffffff
        )
        embed.set_author(name=message.author.name, icon_url=message.author.avatar_url)
        embed.add_field(name="Posted:", value=message.content)

        try:
            await target.send(embed=embed)
            await ctx.send("Message crossposted!")
        except Exception as error:
            await ctx.send(f"Unabled to crosspost: {error}")

    @commands.command(aliases=["mv", "->"])
    @msg_op_or_level(5)
    async def move(self, ctx: Context, message: Message, target: TextChannel):
        """Move a message to a different channel."""
        embed = Embed(
            title=f"Moved message from #{ctx.channel.name}",
            url=message.jump_url,
            color=0xffffff
        )
        embed.set_author(name=message.author.name, icon_url=message.author.avatar_url)
        embed.add_field(name="Posted:", value=message.content)

        try:
            await target.send(embed=embed)
        except Exception as error:
            await ctx.send(f"Unable to send message: {error}")
            return
        try:
            await message.delete()
        except Exception as error:
            await ctx.send(f"Unable to delete message: {error}")
            return

        await ctx.send("Message moved!")

def setup(bot):
    if prefix is not None:
        bot.add_cog(Messages(bot))
    else:
        print("Unable to load messages plugin.")
