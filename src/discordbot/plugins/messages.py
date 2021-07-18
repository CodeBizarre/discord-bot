from datetime import datetime

from discord import TextChannel, Member, Message, Embed, Role
from discord.ext import commands
from discord.ext.commands import Context

from discordbot.core.discord_bot import DiscordBot
from discordbot.core.time_tools import pretty_datetime

VERSION = "3.3b3"


def msg_op_or_permission():
    """
    Check if a user either is the original poster of the message, or has permission.
    """

    async def predicate(ctx: Context):
        # Always show the command as available in help
        if ctx.invoked_with == "help":
            return True

        # Grab the destination channel by its #mention
        try:
            dest_channel = ctx.message.channel_mentions[0]
        except IndexError:
            raise commands.BadArgument("Invalid target channel.")

        # Now check if the user has the manage messages permission in the destination
        if ctx.author.permissions_in(dest_channel).manage_messages:
            # If so we can skip any farther checks
            return True

        # Otherwise split the message into arguments
        arguments = ctx.message.content.split(" ")[1:]

        # Ensure that the first argument is a Discord message link
        prefaces = ("https://discord.com/channels/", "https://discordapp.com/channels/")
        if not arguments[0].startswith(prefaces):
            raise commands.BadArgument("Message must be a Discord message link.")

        # Split the link and grab the destination channel and message id
        split = arguments[0].split("/")
        orig_channel = ctx.guild.get_channel(int(split[5]))
        message_id = int(split[6])

        try:
            target_message = await orig_channel.fetch_message(message_id)
        except Exception as e:
            await ctx.send(f":anger: Unable to process: {e}")
            return

        author = target_message.author

        return author == ctx.author and author.permissions_in(dest_channel).send_messages

    return commands.check(predicate)


class Messages(commands.Cog):
    """Message management plugin.

    Allows cross-posting and moving of messages.
    """

    def __init__(self, bot: DiscordBot):
        self.bot = bot
        self.name = "messages"
        self.version = VERSION

    # Due to some really weird circular import errors, I'm just doing a paste of this here
    async def log_to_channel(self, ctx: Context, target: Member, info: str = None):
        """Send an embed-formatted log of an event to a channel."""
        sid = str(ctx.guild.id)
        channel = None
        enabled = True
        action = ctx.message.content

        if sid in self.db:
            try:
                channel = ctx.guild.get_channel(int(self.db[sid]["log_channel"]))
            except KeyError:
                channel = None
            try:
                enabled = self.db[sid]["log"]
            except KeyError:
                enabled = False
        else:
            channel = ctx.channel
            enabled = False

        if not enabled:
            return

        if info is None:
            info = "No extra information"

        tag = f"{target.name}#{target.discriminator} ({target.id})"

        embed = Embed(
            title=f"{ctx.author.name}#{ctx.author.discriminator} {ctx.command.name}",
            color=0xFF0000,
        )
        embed.set_thumbnail(url=str(ctx.author.avatar_url))
        embed.add_field(name="Action", value=action, inline=False)
        embed.add_field(name="Target", value=tag)
        embed.add_field(name="Info", value=info)
        embed.set_footer(text=pretty_datetime(datetime.now()))

        await channel.send(embed=embed)

    @commands.command(aliases=["xpost", "x-post"])
    @msg_op_or_permission()
    @commands.guild_only()
    async def crosspost(self, ctx: Context, message: Message, target: TextChannel):
        """Cross-post <message> to <target>.
        Message must be a Discord message link.

        Must be the message OP or have manage messages permission.
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
            color=0x7289DA,
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
    @msg_op_or_permission()
    @commands.guild_only()
    async def move(self, ctx: Context, message: Message, target: TextChannel):
        """Move a <message> to a different channel.
        Message must be a Discord message link.

        Must be the message OP or have manage messages permission.
        """
        # Avoid posting to the same channel
        if message.channel == target:
            await ctx.send(":anger: Target must be a different channel.")
            return

        content = message.content

        # Add placeholder content if the message was only an embed
        if len(content) <= 1:
            content = "-"

        # Set up the embed
        embed = Embed(
            title=f"Moved message from #{message.channel.name}",
            url=message.jump_url,
            color=0x7289DA,
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
            await ctx.send(":white_check_mark: Message moved!")
        except Exception as error:
            await ctx.send(f":anger: Unable to send message: {error}")
            return
        try:
            await message.delete()
        except Exception as error:
            await ctx.send(f":anger: Unable to delete message: {error}")
            return

    @commands.group(aliases=["clear"])
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def purge(self, ctx: Context):
        """Purge messages."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help("purge")

    @purge.command(name="self", aliases=["me"])
    @commands.has_permissions(manage_messages=True)
    @commands.guild_only()
    async def purge_self(self, ctx: Context, count: int = 10):
        """Purge messages from yourself.
        Manage messages permission required.
        """
        result = len(
            await ctx.channel.purge(limit=count, check=lambda m: m.author == ctx.author)
        )

        await self.log_to_channel(ctx, ctx.author)

        await ctx.send(
            f":white_check_mark: Purged {result} messages from you in {count}."
        )

    @purge.command(name="bot")
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def purge_bot(self, ctx: Context, count: int = 10):
        """Purge messages sent by the bot.
        Manage messages permission required.
        """
        result = len(
            await ctx.channel.purge(
                limit=count, check=lambda m: m.author.id == ctx.bot.user.id
            )
        )

        await self.log_to_channel(ctx, ctx.author)

        await ctx.send(
            f":white_check_mark: Purged {result} messages from the bot in {count}."
        )

    @purge.command(name="all", aliases=["everyone"])
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def purge_all(self, ctx: Context, count: int = 10):
        """Purge all messages.
        Manage messages permission required.
        """
        result = len(await ctx.channel.purge(limit=count))

        await self.log_to_channel(ctx, ctx.author)

        await ctx.send(f":white_check_mark: Purged {result} messages.")

    @purge.command(name="member", aliases=["user", "target"])
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def purge_member(self, ctx: Context, target: Member, count: int = 10):
        """Purge messages from a member.
        Manage messages permission required.
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
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def purge_group(self, ctx: Context, role: Role, count: int = 10):
        """Purge messages from a role.
        Manage messages permission required.
        """
        result = len(
            await ctx.channel.purge(limit=count, check=lambda m: role in m.author.roles)
        )

        await self.log_to_channel(ctx, ctx.author)

        await ctx.send(
            f":white_check_mark: Purged {result} messages from {role.mention} in {count}."
        )


def setup(bot):
    bot.add_cog(Messages(bot))
