import os
import asyncio
import shutil
import json

from datetime import datetime, timedelta, timezone
from sqlitedict import SqliteDict
from discord import Member, Role, TextChannel, Embed
from discord.ext import commands
from discord.ext.commands import Context

from discord_bot import DiscordBot
from accounts import is_level
from helpers import update_db, pretty_datetime, pretty_timedelta, time_parser

VERSION = "2.5b4"

async def embed_builder(action: str, member: Member, reason: str,
    td: timedelta = None) -> Embed:
    embed = Embed(title=action, color=0xff0000)

    embed.add_field(name="From", value=member.guild.name)
    embed.add_field(name="Reason", value=reason, inline=False)

    try:
        embed.set_author(icon_url=member.guild.icon)
    except Exception:
        pass

    if td is not None:
        embed.add_field(name="Expires In", value=pretty_timedelta(td), inline=False)

    embed.set_footer(text=pretty_datetime(datetime.now()))

    return embed

class Admin(commands.Cog):
    """General purpose administration plugin.

    Features warning, kicking, banning, soft bans, timed bans, and message purging.
    """
    # Coroutine to run in a background thread to check if tempbans are expired
    async def tempban_check(self):
        ts = datetime.now(tz=timezone.utc).timestamp()

        # No servers registered
        if len(self.tempban_db) <= 0:
            return

        for sid in self.tempban_db:
            # No tempbans in this server
            if len(self.tempban_db[sid]) <= 0:
                continue

            # Each tempban in the server
            for uid in self.tempban_db[sid]:
                info = self.tempban_db[sid][uid]

                if ts >= float(info["expires"]):
                    guild = self.bot.get_guild(int(sid))
                    await guild.unban(bot.get_user(uid))

                    del self.tempban_db[sid][uid]
                    update_db(self.sql_db, self.tempban_db, "temp_bans")
                    self.bot.log.info(
                        f"[ADMIN][TEMPBAN][REMOVE] {uid} in <{guild.name}>"
                    )

    # Coroutine to run in a background thread to check if warns are expired
    async def warn_check(self):
        ts = datetime.now(tz=timezone.utc).timestamp()

        # No servers registered
        if len(self.warn_db) <= 0:
            return

        for sid in self.warn_db:
            # No warns in the server
            if len(self.warn_db[sid]) <= 0:
                continue

            guild = self.bot.get_guild(int(sid))

            # Each warn in the server
            for uid in self.warn_db[sid]:
                for i, w in self.warn_db[sid][uid].items():
                    if ts >= float(w["expires"]):
                        del self.warn_db[sid][uid][i]
                        update_db(self.sql_db, self.warn_db, "warns")
                        self.bot.log.info(
                            f"[ADMIN][WARN][REMOVE] {uid}.{i} in <{guild.name}>"
                        )

    # Coroutine to run in a background thread to check if mutes are expired
    async def mute_check(self):
        ts = datetime.now(tz=timezone.utc).timestamp()

        # No servers registered
        if len(self.mute_db) <= 0:
            return

        for sid in self.mute_db:
            # No mutes in this server
            if len(self.mute_db[sid]) <= 0:
                continue

        # Each mute in the server
        for uid, info in self.mute_db[sid].items():
            if ts >= float(info["expires"]):
                guild = self.bot.get_guild(int(sid))

                # Get the mute role
                try:
                    role = guild.get_role(int(self.db[sid]["mute_role"]))
                # Delete the mute from the database if we're unable to get the mute role
                except KeyError:
                    del self.mute_db[sid][uid]
                    break

                # Else get the member and remove the mute role
                target = guild.get_member(int(uid))

                if role in target.roles:
                    await target.remove_roles(role, reason="Auto mute remove.")
                    await target.send(
                        f":speaking_head: Your mute in {guild.name} has expired."
                    )
                else:
                    del self.mute_db[sid][uid]
                    break

                del self.mute_db[sid][uid]
                update_db(self.sql_db, self.mute_db, "mutes")
                self.bot.log.info(
                    f"[ADMIN][MUTE][REMOVE] {target.id} in <{guild.name}>"
                )

    # Background task scheduling system
    async def task_scheduler(self):
        while True:
            try:
                await self.tempban_check()
                await self.warn_check()
                await self.mute_check()
                await asyncio.sleep(60)
            except RuntimeError:
                # Database changed during iteration
                # This is expected when new bans/warns/mutes are added
                continue

    def __init__(self, bot: DiscordBot):
        self.bot = bot
        self.name = "admin"
        self.version = VERSION
        self.backup = True

        # Check the config and make any required backups
        try:
            with open("config/config.json") as cfg:
                self.backup = json.load(cfg)["BackupDB"]
        except Exception as error:
            self.bot.log.error(f"Error loading prefix from config file.\n    - {error}")

        # Set up the database
        db_file = "db/admin.sql"

        if os.path.exists(db_file) and self.backup:
            timestamp = pretty_datetime(datetime.now(), display="FILE")
            try:
                shutil.copyfile(db_file, f"db/backups/admin-{timestamp}.sql")
            except IOError as e:
                error_file = f"db/backups/admin-{timestamp}.sql"
                self.bot.log.error(f"Unable to create file {error_file}\n    - {e}")

        self.sql_db = SqliteDict(
            filename=db_file,
            tablename="admin",
            autocommit=True,
            encode=json.dumps,
            decode=json.loads
        )

        if "admin" not in self.sql_db:
            self.sql_db["admin"] = {}

        if "temp_bans" not in self.sql_db:
            self.sql_db["temp_bans"] = {}

        if "warns" not in self.sql_db:
            self.sql_db["warns"] = {}

        if "mutes" not in self.sql_db:
            self.sql_db["mutes"] = {}

        self.db = self.sql_db["admin"]
        self.tempban_db = self.sql_db["temp_bans"]
        self.warn_db = self.sql_db["warns"]
        self.mute_db = self.sql_db["mutes"]

        asyncio.create_task(self.task_scheduler())

    # Send an embed-formatted log of an event to a channel
    async def log_to_channel(self, ctx: Context, target: Member, info: str = None):
        sid = str(ctx.guild.id)
        channel = None
        enabled = True
        action = ctx.message.content

        # Try and get the config values for the server
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

        # Log the info as an embed
        tag = f"{target.name}#{target.discriminator} ({target.id})"

        embed = Embed(
            title=f"{ctx.author.name}#{ctx.author.discriminator} {ctx.command.name}",
            color=0xff0000
        )
        embed.set_thumbnail(url=str(ctx.author.avatar_url))
        embed.add_field(name="Action", value=action, inline=False)
        embed.add_field(name="Target", value=tag)
        embed.add_field(name="Info", value=info)
        embed.set_footer(text=pretty_datetime(datetime.now()))

        await channel.send(embed=embed)

    @commands.group()
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def admin(self, ctx: Context):
        """Base command for server administrators.

        Run without arguments to view current server settings.
        MUST HAVE SERVER ADMINISTRATOR PERMISSION
        """
        if ctx.invoked_subcommand is not None:
            return

        sid = str(ctx.guild.id)
        log_status = None
        mute_role = None

        # Get the server's config values
        try:
            channel = self.bot.get_channel(int(self.db[sid]["log_channel"]))
            log_status = f"{self.db[sid]['log']}, {channel.mention}"
        except KeyError:
            log_status = "Not set up"
        try:
            role = ctx.guild.get_role(int(self.db[sid]["mute_role"]))
            mute_role = role.name
        except KeyError:
            mute_role = "Not set up"

        # Post them as en embed
        embed = Embed(title="Admin Info", color=0x7289DA)
        embed.add_field(name="Log", value=log_status, inline=True)
        embed.add_field(name="Mute Role", value=mute_role, inline=True)
        embed.set_footer(text=pretty_datetime(datetime.now()))

        await ctx.send(embed=embed)

    @admin.command(name="log")
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def admin_log(self, ctx: Context, enabled: bool, channel: TextChannel = None):
        """Enable/disable to-channel logging and set the log channel.
        MUST HAVE SERVER ADMINISTRATOR PERMISSION
        """
        sid = str(ctx.guild.id)

        # Initialize the server in the database if required
        if sid not in self.db:
            self.db[sid] = {}

        # Set the config values based on user input (or lack thereof for log channel)
        self.db[sid]["log"] = enabled

        if channel is not None:
            self.db[sid]["log_channel"] = str(channel.id)
        else:
            if "log_channel" not in self.db[sid]:
                self.db[sid]["log_channel"] = str(ctx.message.channel.id)
            channel = ctx.message.channel

        update_db(self.sql_db, self.db, "admin")

        embed = Embed(title="Log Settings", color=0xff0000)
        embed.add_field(name="Enabled", value=str(enabled))
        embed.add_field(name="Log Channel", value=channel.mention)

        await ctx.send(embed=embed)

    @admin.command(name="role")
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def admin_role(self, ctx: Context, role: Role):
        """Set the mute role for the server.
        MUST HAVE SERVER ADMINISTRATOR PERMISSION
        """
        sid = str(ctx.guild.id)

        # Initialize the server in the database if required
        if sid not in self.db:
            self.db[sid] = {}

        # Set the mute role
        self.db[sid]["mute_role"] = str(role.id)

        update_db(self.sql_db, self.db, "admin")

        await ctx.send(f":white_check_mark: Mute role set to: {role.name}.")

    @commands.command()
    @is_level(6)
    async def kick(self, ctx: Context, target: Member, *, reason: str = None):
        """Kick a member from the server.
        Level 6 required
        """
        embed = await embed_builder("Kicked", target, reason)

        await target.send(embed=embed)

        await target.kick(reason=reason)

        tag = f"{target.name}#{target.discriminator}"
        await ctx.send(f":white_check_mark: Kicked {tag} for {reason}")
        await self.log_to_channel(ctx, target, reason)

    @commands.command(aliases=["sban"])
    @is_level(7)
    async def softban(self, ctx: Context, target: Member, purge: int = 1,
        *, reason: str = None):
        """Softban (kick and purge messages) a member from the server.
        Level 7 required
        """
        embed = await embed_builder("Kicked", target, reason)

        await target.send(embed=embed)

        await target.ban(reason=f"Softbanned: {reason}", delete_message_days=purge)
        await target.unban(reason="Softban removal")

        tag = f"{target.name}#{target.discriminator}"
        await ctx.send(f":white_check_mark: Softbanned {tag} for {reason}")
        await self.log_to_channel(ctx, target, reason)

    @commands.command()
    @is_level(8)
    async def ban(self, ctx: Context, target: Member, purge: int = 7,
        *, reason: str = None):
        """Ban a member from the server.
        Level 8 required
        """
        embed = await embed_builder("Permanently Banned", target, reason)

        await target.send(embed=embed)

        await target.ban(reason=reason, delete_message_days=purge)

        tag = f"{target.name}#{target.discriminator}"
        await ctx.send(f":white_check_mark: Banned {tag} for {reason}")
        await self.log_to_channel(ctx, target, reason)

    @commands.command(aliases=["tban"])
    @is_level(8)
    async def tempban(self, ctx: Context, target: Member, length: int, span: str,
        *, reason: str = None):
        """Temporarily ban a member from the server.
        For timing, plural and non-plural spans are accepted (Day, days, minutes, etc).
        Use "max" as the span for psuedo-permanence (10 years).
        Level 8 required
        """
        sid = str(ctx.guild.id)

        # Initialize the server in the tempban database if required
        if sid not in self.tempban_db:
            self.tempban_db[sid] = {}

        # Get the current UTC time, a future time from time_parser, and the difference
        now = datetime.now(tz=timezone.utc)
        future = await time_parser(span, length, now)
        length = future - now

        embed = await embed_builder("Temporarily Banned", target, reason, length)

        await target.send(embed=embed)

        await target.ban(reason=reason, delete_message_days=0)

        # Add the tempban to the database
        self.tempban_db[sid][target.id] = {
            "issued_by": str(ctx.author.id),
            "reason": reason,
            "expires": str(future.timestamp())
        }

        update_db(self.sql_db, self.tempban_db, "temp_bans")

        tag = f"{target.name}#{target.discriminator}"
        await ctx.send(f":white_check_mark: Tempbanned {tag} for {reason}")
        await self.log_to_channel(ctx, target, reason)

    @commands.group()
    @commands.guild_only()
    async def purge(self, ctx: Context):
        """Purge messages."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help("purge")

    @purge.command(name="self", aliases=["me"])
    @commands.guild_only()
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

    @commands.command()
    @commands.guild_only()
    @is_level(4)
    async def warn(self, ctx: Context, target: Member, length: int, span: str,
        *, reason: str):
        """Warn a member.
        For timing, plural and non-plural spans are accepted (Day, days, minutes, etc).
        Use "max" as the span for psuedo-permanence (10 years).
        Level 4 required
        """
        sid = str(ctx.guild.id)
        uid = str(target.id)
        warn_count = 1

        # Initialize the server in the warn database if required
        if sid not in self.warn_db:
            self.warn_db[sid] = {}

        # Add 1 to the amount of warns the user may already have
        if uid in self.warn_db[sid]:
            for _ in self.warn_db[sid][uid]:
                warn_count += 1

        # Get the current UTC time, a future time from time_parser, and the difference
        now = datetime.now(tz=timezone.utc)
        future = await time_parser(span, length, now)
        length = future - now

        embed = await embed_builder("Warned", target, reason, length)

        await target.send(embed=embed)
        await target.send(f":warning: This is warning #{warn_count}.")
        await ctx.send(
            f":warning: Warning {warn_count} issued to {target.name} for {reason}"
        )

        # Add the warn to the database
        if uid not in self.warn_db[sid]:
            self.warn_db[sid][uid] = {}

        def db_check(count: int) -> int:
            if str(count) in self.warn_db[sid][uid]:
                count += 1
                return db_check(count)
            else:
                return count

        warn_count = db_check(warn_count)

        warning = {
            "issued_by": str(ctx.author.id),
            "reason": reason,
            "expires": str(future.timestamp())
        }
        self.warn_db[sid][uid][str(warn_count)] = warning

        update_db(self.sql_db, self.warn_db, "warns")
        await self.log_to_channel(ctx, target, reason)

    @commands.group()
    @commands.guild_only()
    async def warns(self, ctx: Context):
        """Base command to manage warns."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help("warns")

    @warns.command(name="list", aliases=["find", "lookup", "member"])
    @commands.guild_only()
    async def warns_list(self, ctx: Context, target: Member = None):
        """List all active warns of yourself or another member.
        Invoke without argument to view your own warns.
        Level 4 required to view other Members' warns
        """
        sid = str(ctx.guild.id)

        if sid not in self.warn_db:
            await ctx.send(":anger: Server has no warns.")
            return

        if target is None:
            target = ctx.author

        uid = str(target.id)

        if uid not in self.warn_db[sid]:
            await ctx.send(":anger: Member has no warns.")
            return

        if target is not ctx.author:
            try:
                level = self.bot.accounts[sid][str(ctx.author.id)]
            except KeyError:
                await ctx.send(":anger: You must have an account on this server.")
                return
            if level < 4:
                await ctx.send(":anger: Must be level 4 to view other users' warns.")
                return

        embed = Embed(
            title=f"{target.name}#{target.discriminator}'s Warns",
            color=0xff0000
        )

        warn_count = len(self.warn_db[sid][uid])

        embed.add_field(
            name="Total warns",
            value=str(warn_count),
            inline=False
        )

        # Build the fields of the embed by iterating through a user's warns
        for i, w in self.warn_db[sid][uid].items():
            # Get the current time and the expiry time of the warn
            now = datetime.now(tz=timezone.utc)
            then = datetime.fromtimestamp(float(w["expires"]), tz=timezone.utc)
            # Get a timedelta of the difference between the times
            result = then - now
            expires = pretty_timedelta(result)
            # Add that plus the rest of the info to an embed field
            issuer = ctx.guild.get_member(int(w["issued_by"]))
            name = f"{issuer.name}#{issuer.discriminator}"

            embed.add_field(
                name=i,
                value=f"By: {name}\nReason: {w['reason']}\nExpires: {expires}",
                inline=True
            )

        embed.set_footer(text=pretty_datetime(datetime.now()))

        await ctx.send(embed=embed)

    @warns.command(name="remove", aliases=["delete", "del"])
    @commands.guild_only()
    @is_level(4)
    async def warns_remove(self, ctx: Context, target: Member, number: int):
        """Remove a warning from a member.
        Level 4 required
        """
        sid = str(ctx.guild.id)
        tid = str(target.id)

        if sid not in self.warn_db:
            await ctx.send(":anger: Server has no warns.")
            return
        elif tid not in self.warn_db[sid]:
            await ctx.send(":anger: Member has no warns.")
            return

        for i, w in self.warn_db[sid][tid].items():
            if i == str(number):
                del self.warn_db[sid][tid][i]
                await ctx.send(f":white_check_mark: Warn #{i} (`{w['reason']}`) removed.")
                await target.send(
                    f"Warn #{i} for `{w['reason']}` in {ctx.guild.name} has been removed."
                )
                break

    @commands.command()
    @commands.guild_only()
    @is_level(4)
    async def mute(self, ctx: Context, target: Member, length: int, span: str,
        *, reason: str):
        """Set a member to the mute role.
        For timing, plural and non-plural spans are accepted (Day, days, minutes, etc).
        Use "max" as the span for psuedo-permanence (10 years).
        Level 4 required
        """
        sid = str(ctx.guild.id)
        uid = str(target.id)
        mute_role = None

        # Try to get the mute role from the server
        try:
            mute_role = ctx.guild.get_role(int(self.db[sid]["mute_role"]))
        except KeyError:
            await ctx.send(":anger: Server has no mute role set.")
            return

        # Initialize the server in the mute database if required
        if sid not in self.mute_db:
            self.mute_db[sid] = {}

        # Get the current UTC time, a future time from time_parser, and the difference
        now = datetime.now(tz=timezone.utc)
        future = await time_parser(span, length, now)
        length = future - now
        time = pretty_timedelta(length)

        embed = await embed_builder("Muted", target, reason, length)

        await target.send(embed=embed)
        await ctx.send(
            f":white_check_mark: {target.name} muted for {reason}, expires in {time}"
        )

        # Set the user to the muted role
        await target.add_roles(mute_role)

        # Add the mute to the database
        mute = {
            "issued_by": str(ctx.author.id),
            "reason": reason,
            "expires": str(future.timestamp())
        }

        self.mute_db[sid][uid] = mute

        update_db(self.sql_db, self.mute_db, "mutes")
        await self.log_to_channel(ctx, target, reason)

    @commands.command()
    @commands.guild_only()
    @is_level(4)
    async def unmute(self, ctx: Context, target: Member):
        """Unmute a member early.
        Level 4 required
        """
        sid = str(ctx.guild.id)
        uid = str(target.id)
        mute_role = None

        # Try to get the mute role from the server
        try:
            mute_role = ctx.guild.get_role(int(self.db[sid]["mute_role"]))
        except KeyError:
            await ctx.send(":anger: This server has no mute role set.")
            return

        if sid not in self.mute_db:
            await ctx.send(":anger: This server has no mutes.")
            return

        if uid not in self.mute_db[sid]:
            await ctx.send(":anger: This member is not muted.")
            return

        await target.send(f":speaking_head: You have been unmuted in {ctx.guild.name}.")
        await ctx.send(f":speaking_head: Unmuted {target.name}.")

        # Remove the mute role and delete the entry from the database
        await target.remove_roles(mute_role)
        del self.mute_db[sid][uid]

        update_db(self.sql_db, self.mute_db, "mutes")

def setup(bot):
    bot.add_cog(Admin(bot))

def teardown(bot):
    bot.cogs["Admin"].sql_db.close()
    bot.remove_cog("Admin")
