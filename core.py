import json

from datetime import datetime
from discord import Game, Message, Guild, Embed, AuditLogAction, Member, User, TextChannel
from discord.ext import commands
from discord.ext.commands import Context, Cog

from discord_bot import DiscordBot
from helpers import update_db, pretty_datetime

VERSION = "1.0b4"

# Exportable check for if the user is a botmaster
def is_botmaster():
    async def predicate(ctx: Context):
        return str(ctx.author.id) in ctx.bot.botmasters
    return commands.check(predicate)

class Core(commands.Cog):
    """Core features."""
    def __init__(self, bot: DiscordBot):
        self.bot = bot
        self.name = "core"
        self.version = VERSION

        try:
            with open("config/config.json") as cfg:
                config = json.load(cfg)
                self.bot.botmasters = config["Botmasters"]
        except Exception as error:
            self.bot.log.error(f"Error loading config for Core module:\n    - {error}")

    ## Checks
    # Global check for if the user is blocked
    async def bot_check(self, ctx):
        return str(ctx.author.id) not in self.bot.blocklist

    ## Events
    @Cog.listener()
    async def on_guild_join(self, guild: Guild):
        sid = str(guild.id)

        self.bot.log.info(f"[JOIN] {guild.name}")

        if sid not in self.bot.servers:
            self.bot.servers[sid] = {}
            update_db(self.bot.db, self.bot.servers, "servers")

    @Cog.listener()
    async def on_guild_remove(self, guild: Guild):
        sid = str(guild.id)

        self.bot.log.info(f"[LEAVE] {guild.name}")

        if sid in self.bot.servers:
            self.bot.servers.pop(sid)
            update_db(self.bot.db, self.bot.servers, "servers")

    @Cog.listener()
    async def on_message(self, msg: Message):
        # Log messages to the console/log file if enabled
        if self.bot.log_messages:
            timestamp = pretty_datetime(datetime.now(), display="TIME")
            message = f"[{msg.guild} - #{msg.channel}] <{msg.author}>: {msg.content}"

            self.bot.log.info(f"-{timestamp}- {message}")

    @Cog.listener()
    async def on_message_edit(self, former: Message, latter: Message):
        sid = str(former.guild.id) if former.guild is not None else None

        # Embeds cause message edit events even if the user didn't edit them
        if former.content == latter.content and former.embeds != latter.embeds:
            return

        # Log the edit to the console/log file if enabled
        if self.bot.log_edits:
            timestamp = pretty_datetime(datetime.now(), display="TIME")

            self.bot.log.info(f"-{timestamp}- [EDIT] [{former.guild}] #{former.channel}")
            self.bot.log.info(f"[BEFORE] <{former.author}>: {former.content}")
            self.bot.log.info(f"[AFTER] <{latter.author}>: {latter.content}")

        # Process the commands from the message afterwards if enabled
        if self.bot.cmd_on_edit:
            await self.bot.process_commands(latter)

        # If this is a DM, we don't need to try and log to channel or report ghosts
        if sid is not None:
            # Check if the server should report mention deletes
            try:
                report_ghosts = self.bot.servers[sid]["report_ghosts"]
            except KeyError:
                # This server is not configured.
                report_ghosts = False

            if report_ghosts and former.author.id is not self.bot.user.id:
                title = f"A message from {former.author.mention} was edited removing"
                difference = former.mentions

                if difference != latter.mentions:
                    for mention in latter.mentions:
                        if mention in difference:
                            difference.remove(mention)

                    mentions = [f"{m.name}#{m.discriminator}" for m in difference]
                    await former.channel.send(f"{title} mention(s) from: {mentions}")
                elif former.mention_everyone and not latter.mention_everyone:
                    await former.channel.send(f"{title} an Everyone or Here mention")
                elif former.role_mentions != latter.role_mentions:
                    difference = former.role_mentions - latter.role_mentions
                    mentions = [f"{r.name}" for r in difference]
                    await former.channel.send(f"{title} role mention(s): {mentions}")

            # Log the edit to a channel if the server has it set up
            try:
                if self.bot.servers[sid]["log_edits"]:
                    guild = former.guild
                    channel = guild.get_channel(int(self.bot.servers[sid]["log_channel"]))

                    embed = Embed(title="Message Edited", color=0xff0000)
                    embed.add_field(
                        name=f"Edited by {former.author.name}#{former.author.discriminator}",
                        value=f"Edited in {former.channel.mention}. UID: {former.author.id}"
                    )
                    embed.add_field(name="Before", value=former.content, inline=False)
                    embed.add_field(name="After", value=latter.content, inline=False)

                    await channel.send(embed=embed)
            except KeyError:
                pass

    @Cog.listener()
    async def on_message_delete(self, msg: Message):
        sid = str(msg.guild.id) if msg.guild is not None else None

        # Log the delete to the console/log file if enabled
        if self.bot.log_deletes:
            timestamp = pretty_datetime(datetime.now(), display="TIME")

            header = f"-{timestamp}- [DELETE] "
            content = f"[{msg.guild}] #{msg.channel} <{msg.author}>: {msg.content}"

            self.bot.log.info(f"{header} {content}")

        # If this is a DM, we don't need to try and log to channel or report ghosts
        if sid is not None:
            # Check if the server should report mention deletes
            try:
                report_ghosts = self.bot.servers[sid]["report_ghosts"]
            except KeyError:
                # This server is not configured.
                report_ghosts = False

            if report_ghosts and msg.author.id is not self.bot.user.id:
                title = f"A message from {msg.author.mention} was removed mentioning"

                if len(msg.mentions) > 0:
                    mentions = [f"{m.name}#{m.discriminator}" for m in msg.mentions]
                    await msg.channel.send(f"{title}: {mentions}")
                elif msg.mention_everyone:
                    await msg.channel.send(f"{title}: Everyone or Here")
                elif len(msg.role_mentions) > 0:
                    mentions = [f"{r.name}" for r in msg.role_mentions]
                    await msg.channel.send(f"{title} role: {mentions}")

            # Log the delete to a channel if the server has it set up
            try:
                if self.bot.servers[sid]["log_deletes"]:
                    # Try to get the user who deleted the message, not reliable
                    action = await msg.guild.audit_logs(
                        limit=1,
                        action=AuditLogAction.message_delete
                    ).flatten()

                    who = action[0].user

                    guild = msg.guild
                    channel = guild.get_channel(int(self.bot.servers[sid]["log_channel"]))

                    embed = Embed(title="Message Deleted", color=0xff0000)
                    embed.add_field(
                        name="Last message delete action performed by:",
                        value=f"{who.name}#{who.discriminator} or a bot",
                        inline=False
                    )
                    embed.add_field(
                        name=f"Author - {msg.author.name}#{msg.author.discriminator}",
                        value=f"Deleted from {msg.channel.mention} - UID: {msg.author.id}"
                    )
                    embed.add_field(name="Message", value=msg.content, inline=False)

                    await channel.send(embed=embed)
            except KeyError:
                pass

    @Cog.listener()
    async def on_command(self, ctx: Context):
        # Log the command to the console/log file if enabled
        if self.bot.log_commands:
            timestamp = pretty_datetime(datetime.now(), display="TIME")

            command = ctx.message.content
            author = ctx.author

            location = f"[{ctx.guild}] - #{ctx.message.channel}"
            header = f"-{timestamp}- [COMMAND] `{command}`"

            self.bot.log.info(f"{header} by `{author}` in `{location}`")

        if self.bot.delete_cmds:
            try:
                await ctx.message.delete(delay=2)
            except Exception as e:
                self.bot.log.warning(f"Unable to delete command message:\n    - {e}")

    @Cog.listener()
    async def on_command_error(self, ctx: Context, error):
        if isinstance(error, commands.NoPrivateMessage):
            await ctx.send(f":anger: This command is not available in DMs.")
        elif isinstance(error, commands.CommandNotFound):
            # Ignore commands that don't exist
            pass
        elif isinstance(error, commands.TooManyArguments):
            await ctx.send(":anger: Too many arguments passed.")
            await ctx.send_help(ctx.command)
        elif isinstance(error, commands.BadArgument):
            await ctx.send(f":anger: {error}")
            await ctx.send_help(ctx.command)
        elif isinstance(error, commands.MissingPermissions):
            await ctx.send(":anger: You do not have the required permissions.")
        elif isinstance(error, commands.BotMissingPermissions):
            await ctx.send(":anger: I don't have permission to do that.")
        elif isinstance(error, commands.CheckFailure):
            await ctx.send(
                f":anger: You do not meet one or more requirements to use this command."
            )
        elif isinstance(error, AttributeError):
            raise AttributeError from error
        else:
            # For remaining errors, simply sending it to the issuing channel is enough
            await ctx.send(f":anger: Error: {error}")

    ## Commands
    @commands.command()
    @is_botmaster()
    async def shutdown(self, ctx: Context):
        """Shut the bot down compeletely.
        Botmaster required.
        """
        await ctx.send(":desktop: Shutting down.")
        await self.bot.logout()

    @commands.command()
    async def ping(self, ctx: Context):
        """Ping/pong test."""
        await ctx.send(f":ping_pong: Pong {ctx.author.mention}")

    @commands.command()
    @is_botmaster()
    async def status(self, ctx: Context, *, status: str):
        """Set the bot to 'Playing <status>'."""
        activity = Game(name=status)
        try:
            await self.bot.change_presence(activity=activity)
            await ctx.send(":white_check_mark: Status changed.")
        except Exception as e:
            await ctx.send(f":anger: Unable to change status: {e}")

    @commands.command()
    async def info(self, ctx: Context):
        """Show the bot's mission control."""
        embed = Embed(title="Status", color=0x7289DA)

        embed.add_field(name="Time", value=pretty_datetime(datetime.now(), "FULL"))
        embed.add_field(name="Version", value=self.bot.version)

        embed.add_field(
            name="User",
            value=f"{self.bot.user} ({self.bot.user.id})",
            inline=False
        )

        embed.add_field(name="Plugins", value=f"[{', '.join(self.bot.plugins)}]")
        embed.add_field(name="Servers", value=str(len(self.bot.servers)))

        # Just in case something happened initializing the app info
        if self.bot.app_info is not None:
            embed.set_author(
                name=self.bot.app_info.name,
                icon_url=self.bot.app_info.icon_url
            )

        embed.set_footer(text="https://github.com/Aurexine/discord-bot")

        await ctx.send(embed=embed)

    @commands.command(aliases=["bl"])
    @is_botmaster()
    async def block(self, ctx: Context, target: User, block = True):
        """Add or remove a user from the block list.
        Botmaster required.
        """
        uid = str(target.id)

        if uid in self.bot.blocklist:
            # Trying to block a user who is already blocked
            if block:
                await ctx.send(f":anger: {target.name} is already blocked.")
            # Unblock a user.
            else:
                self.bot.blocklist.remove(uid)
                await ctx.send(
                    f":white_check_mark: {target.name} unblocked."
                )
        else:
            # Add a user to the blocklist
            if block:
                self.bot.blocklist.append(uid)
                await ctx.send(f":white_check_mark: {target.name} blocked.")
            # Trying to remove a user who is not blocklisted
            else:
                await ctx.send(f":anger: {target.name} is not blocked.")

        update_db(self.bot.db, self.bot.blocklist, "blocklist")

    @commands.group(name="logs", aliases=["log"])
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def cmd_logs(self, ctx: Context):
        """Command to change settings for logging edited or deleted messages.

        Running the command without arguments will display your server's currect settings.
        MUST HAVE SERVER ADMINISTRATOR PERMISSION
        """
        if ctx.invoked_subcommand is None:
            embed = Embed(title="Log Settings", color=0x7289DA)
            sid = str(ctx.guild.id)

            try:
                guild = ctx.bot.get_guild(int(sid))
                channel = guild.get_channel(int(self.bot.servers[sid]["log_channel"]))

                embed.add_field(
                    name="Log Edits",
                    value=str(self.bot.servers[sid]["log_edits"])
                )
                embed.add_field(
                    name="Log Deletes",
                    value=str(self.bot.servers[sid]["log_deletes"])
                )
                embed.add_field(
                    name="Log Channel",
                    value=channel.mention
                )
            except KeyError:
                await ctx.send("Server is not set up or channels have been changed.")
                return

            await ctx.send(embed=embed)

    @cmd_logs.command(name="edits")
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def cmd_logs_edits(self, ctx: Context, enabled: bool):
        """Set logging of edited messages to the server's log channel.
        MUST HAVE SERVER ADMINISTRATOR PERMISSION
        """
        sid = str(ctx.guild.id)

        if sid not in self.bot.servers:
            self.bot.servers[sid] = {}

        self.bot.servers[sid]["log_edits"] = enabled
        update_db(self.bot.db, self.bot.servers, "servers")

        await ctx.send(f":white_check_mark: Logging message edits set to {enabled}.")

    @cmd_logs.command(name="deletes")
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def cmd_logs_deletes(self, ctx: Context, enabled: bool):
        """Set logging of deleted messages to the server's log channel.
        MUST HAVE SERVER ADMINISTRATOR PERMISSION
        """
        sid = str(ctx.guild.id)

        if sid not in self.bot.servers:
            self.bot.servers[sid] = {}

        self.bot.servers[sid]["log_deletes"] = enabled
        update_db(self.bot.db, self.bot.servers, "servers")

        await ctx.send(f":white_check_mark: Logging message deletes set to {enabled}.")

    @cmd_logs.command(name="channel")
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def cmd_logs_channel(self, ctx: Context, channel: TextChannel):
        """Set the server's message logging channel.
        MUST HAVE SERVER ADMINISTRATOR PERMISSION
        """
        sid = str(ctx.guild.id)

        if sid not in self.bot.servers:
            self.bot.servers[sid] = {}

        self.bot.servers[sid]["log_channel"] = str(channel.id)
        update_db(self.bot.db, self.bot.servers, "servers")

        await ctx.send(f":white_check_mark: Logging channel set to {channel.mention}.")

    @commands.command(aliases=["ghost", "pings"])
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def ghosts(self, ctx: Context, enabled: bool = True):
        """Set per-server reporting of deleted messages contianing mentions (pings).
        This causes a 'Ghost' notification on the client of the user who was mentioned.

        If enabled, the bot will post a message showing all users mentioned.
        """
        sid = str(ctx.guild.id)

        if sid not in self.bot.servers:
            self.bot.servers[sid] = {}

        self.bot.servers[sid]["report_ghosts"] = enabled
        update_db(self.bot.db, self.bot.servers, "servers")

        await ctx.send(f":white_check_mark: Ghost reporting set to {enabled}.")

    @commands.command(aliases=["who", "identify"])
    @commands.guild_only()
    async def whois(self, ctx: Context, target: Member = None):
        """Display basic information about <target>.

        Running the command without arguments will show information about you.
        """
        if target is None: target = ctx.author

        embed = Embed(title=f"{target.name}#{target.discriminator}", color=0x7289DA)
        embed.set_thumbnail(url=str(target.avatar_url))

        embed.add_field(
            name="Joined At",
            value=f"{pretty_datetime(target.joined_at)}"
        )
        embed.add_field(
            name="Nickname",
            value=f"{target.nick}"
        )
        embed.add_field(
            name="Roles",
            value=f"{[r.name for r in target.roles[1:]]}",
            inline=False
        )

        await ctx.send(embed=embed)

    @commands.command()
    async def prefix(self, ctx: Context):
        """Display the bot's command prefix.
        Only useful when MentionCommands is enabled.
        """
        await ctx.send(f"Command prefix is: `{self.bot.config_prefix}`")

def setup(bot):
    bot.add_cog(Core(bot))