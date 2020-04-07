import asyncio
import json

from discord import TextChannel, Member, Message, Embed
from discord import HTTPException
from discord.ext import commands
from discord.ext.commands import Context

from main import get_account
from helpers import pretty_datetime

VERSION = "2.2b1"

# Get the config file to grab the command prefix
prefix = None

try:
    with open("config/config.json") as cfg:
        prefix = json.load(cfg)["Prefix"]
except Exception as error:
    print(f"Error loading prefix from configuration file.\n    - {error}")

def msg_op_or_level(required=10):
    """See if the user is the OP of the message, or high enough level otherwise."""
    async def predicate(ctx: Context):
        uid = str(ctx.author.id)
        loop = ctx.bot.loop

        # If the check if being ran through the help command always pass
        # This is so the help command will correctly display that everyone can use this
        if ctx.invoked_with == "help":
            ctx.message.content = ""
            return True

        # Split the message into arguments and fetch the requested message
        # This check is specifically for the move/crosspost commands
        # Therefore it can be assuemed args[1] will be a message id
        args = ctx.message.content.split(" ")

        exc = asyncio.run_coroutine_threadsafe(ctx.fetch_message(args[1]), loop)

        while not exc.done():
            await asyncio.sleep(0.1)

        try:
            target = exc.result()
        except HTTPException:
            return False

        # User ID of the message open
        tid = str(target.author.id)

        # If the user is the OP
        if uid == tid:
            return True
        # Else try to fetch the user's account
        else:
            try:
                user_level = get_account(ctx.guild, ctx.author)
            except KeyError as e:
                await ctx.send(f"KeyError: {e}")
                return False
            else:
                return user_level >= required

    return commands.check(predicate)

class Messages(commands.Cog):
    """Message management plugin.

    Allows cross-posting and moving of messages.
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.name = "messages"

    @commands.command(aliases=["xpost", "x-post"])
    @msg_op_or_level(5)
    async def crosspost(self, ctx: Context, message: Message, target: TextChannel):
        """Cross-post a <Message> (Message) to another <Target> (TextChannel).
        Must be <Message> OP or level 5
        """
        # Avoid posting to the same channel
        if message.channel == target:
            await ctx.send("Target must be a different channel.")
            return

        # Image only messages
        content = message.content

        # Add placeholder content if the message was only an image
        if len(content) <= 1:
            content = "-"

        # Set up the embed
        embed = Embed(
            title=f"X-Post from #{ctx.channel.name}",
            url=message.jump_url,
            color=0x7289DA
        )
        embed.set_author(name=message.author.name, icon_url=message.author.avatar_url)
        embed.add_field(name="Posted:", value=content)

        # Set the embedded image to the first image attachment of the message if any exist
        if len(message.attachments) > 0:
            embed.set_image(url=message.attachments[0].url)
        # Else check if the message ends in an image link and add that instead
        elif message.content.endswith(("jpg", "jpeg", "png", "gif", "bmp")):
            items = message.content.split(" ")
            embed.set_image(url=items[len(items) - 1])

        try:
            await target.send(embed=embed)
            await ctx.send("Message crossposted!")
        except Exception as error:
            await ctx.send(f"Unabled to crosspost: {error}")

    @commands.command(aliases=["mv", "->"])
    @msg_op_or_level(5)
    async def move(self, ctx: Context, message: Message, target: TextChannel):
        """Move a <Message> (Message) to a different <Target> (TextChannel).
        Must be <Message> OP or level 5
        """
        # Avoid posting to the same channel
        if message.channel == target:
            await ctx.send("Target must be a different channel.")

        # Image only messages
        content = message.content

        # Add placeholder content if the message was only an image
        if len(content) <= 1:
            content = "-"

        # Set up the embed
        embed = Embed(
            title=f"Moved message from #{ctx.channel.name}",
            url=message.jump_url,
            color=0x7289DA
        )
        embed.set_author(name=message.author.name, icon_url=message.author.avatar_url)
        embed.add_field(name="Posted:", value=content)

        # Set the embedded image to the first image attachment of the message if any exist
        if len(message.attachments) > 0:
            embed.set_image(url=message.attachments[0].url)
        # Else check if the message ends in an image link and add that instead
        elif message.content.endswith(("jpg", "jpeg", "png", "gif", "bmp")):
            items = message.content.split(" ")
            embed.set_image(url=items[len(items) - 1])

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
