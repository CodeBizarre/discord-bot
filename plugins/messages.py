import asyncio
import json

from discord import TextChannel, Member, Message, Embed, Role
from discord import HTTPException
from discord.ext import commands
from discord.ext.commands import Context

from core.discord_bot import DiscordBot
from core.time_tools import pretty_datetime
from core.plugins.accounts import is_level

VERSION = "3.1b2"

def msg_op_or_level(required=4):
    """
    Check if a user is either high enough level, or the original poster of the message.
    """
    async def predicate(ctx: Context):
        # Always show the command as available in help
        if ctx.invoked_with == "help": return True

        # First check if the user is a high enough level to bypass the check
        # This is far more efficient than the previous method
        if ctx.bot.accounts[str(ctx.guild.id)][str(ctx.author.id)] >= required:
            return True

        # Otherwise, start the process of checking if the command author is the OP
        # Split the message into arguments
        arguments = ctx.message.content.split(" ")[1:]

        # Ensure that the first argument is a Discord message link
        if not arguments[0].startswith("https://discordapp.com/channels/"):
            raise commands.BadArgument("Message must be a Discord message link.")

        # Split the link and grab the channel and message ids
        split = arguments[0].split("/")
        channel = int(split[4])
        message = int(split[5])

        # Run a threadsafe coroutine to get the target message from the link
        exc = asyncio.run_coroutine_threadsafe(
            ctx.guild.get_channel(channel).fetch_message(message),
            ctx.bot.loop
        )

        while not exc.done():
            await asyncio.sleep(0.1)

        try:
            target = exc.result()
        except HTTPException:
            return False

        return target.author == ctx.author

    return commands.check(predicate)

class Messages(commands.Cog):
    """Message management plugin.

    Allows cross-posting and moving of messages.
    """
    def __init__(self, bot: DiscordBot):
        self.bot = bot
        self.name = "messages"
        self.version = VERSION
        # Try to grab the log to channel function from the admin plugin if it's loaded
        try:
            self.log_to_channel = self.bot.cogs["Admin"].log_to_channel
        except KeyError:
            # Otherwise create a placeholder function that will log to console instead
            async def ltc(ctx: Context, member: Member, info: str = None):
                self.bot.log.info(
                    f"[MESSAGES] [{ctx.guild.name}] <{ctx.author}> " \
                    f"{ctx.message.content}"
                )
            self.log_to_channel = ltc

    @commands.command(aliases=["xpost", "x-post"])
    @commands.guild_only()
    @msg_op_or_level(4)
    async def crosspost(self, ctx: Context, message: Message, target: TextChannel):
        """Cross-post <message> to <target>.
        Message must be a Discord message link.

        Must be the message OP or level 5
        """
        # Avoid posting to the same channel
        if message.channel == target:
            await ctx.send(":anger: Target must be a different channel.")
            return

        content = message.content

        # Add placeholder content if the message was only an embed
        if len(content) <= 1:
            content = "-"

        embed = Embed(
            title=f"X-Post from #{message.channel.name}",
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
            await ctx.send(":white_check_mark: Message crossposted!")
        except Exception as error:
            await ctx.send(f":anger: Unable to crosspost: {error}")

    @commands.command(aliases=["mv", "->"])
    @commands.guild_only()
    @msg_op_or_level(4)
    async def move(self, ctx: Context, message: Message, target: TextChannel):
        """Move a <message> to a different channel.
        Message must be a Discord message link.

        Must be the message OP or level 5
        """
        # Avoid posting to the same channel
        if message.channel == target:
            await ctx.send(":anger: Target must be a different channel.")

        content = message.content

        # Add placeholder content if the message was only an embed
        if len(content) <= 1:
            content = "-"

        # Set up the embed
        embed = Embed(
            title=f"Moved message from #{message.channel.name}",
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
            await ctx.send(f":anger: Unable to send message: {error}")
            return
        try:
            await message.delete()
        except Exception as error:
            await ctx.send(f":anger: Unable to delete message: {error}")
            return

        await ctx.send(":white_check_mark: Message moved!")

    @commands.group()
    @commands.guild_only()
    async def purge(self, ctx: Context):
        """Purge messages."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help("purge")

    @purge.command(name="self", aliases=["me"])
    @commands.guild_only()
    @is_level(5)
    async def purge_self(self, ctx: Context, count: int = 10):
        """Purge messages from yourself."""
        result = len(
            await ctx.channel.purge(limit=count, check=lambda m: m.author == ctx.author)
        )

        await self.log_to_channel(ctx, ctx.author)

        await ctx.send(
            f":white_check_mark: Purged {result} messages from you in {count}."
        )

    @purge.command(name="bot")
    @commands.guild_only()
    @is_level(5)
    async def purge_bot(self, ctx: Context, count: int = 10):
        """Purge messages sent by the bot.
        Level 5 required
        """
        result = len(
            await ctx.channel.purge(
                limit=count,
                check=lambda m: m.author.id == ctx.bot.user.id
            )
        )

        await self.log_to_channel(ctx, ctx.author)

        await ctx.send(
            f":white_check_mark: Purged {result} messages from the bot in {count}."
        )

    @purge.command(name="all", aliases=["everyone"])
    @commands.guild_only()
    @is_level(5)
    async def purge_all(self, ctx: Context, count: int = 10):
        """Purge all messages.
        Level 5 required
        """
        result = len(await ctx.channel.purge(limit=count))

        await self.log_to_channel(ctx, ctx.author)

        await ctx.send(
            f":white_check_mark: Purged {result} messages."
        )

    @purge.command(name="member", aliases=["user", "target"])
    @commands.guild_only()
    @is_level(5)
    async def purge_member(self, ctx: Context, target: Member, count: int = 10):
        """Purge messages from a member.
        Level 5 required
        """
        result = len(
            await ctx.channel.purge(limit=count, check=lambda m: m.author == target)
        )

        await self.log_to_channel(ctx, target)

        mention = target.mention
        await ctx.send(
            f":white_check_mark: Purged {result} messages from {mention} in {count}."
        )

    @purge.command(name="role", aliases=["group"])
    @commands.guild_only()
    @is_level(5)
    async def purge_group(self, ctx: Context, role: Role, count: int = 10):
        """Purge messages from a role.
        Level 5 required
        """
        result = len(
            await ctx.channel.purge(limit=count,check=lambda m: role in m.author.roles)
        )

        await self.log_to_channel(ctx, ctx.author)

        await ctx.send(
            f":white_check_mark: Purged {result} messages from {role.mention} in {count}."
        )

def setup(bot):
    bot.add_cog(Messages(bot))
