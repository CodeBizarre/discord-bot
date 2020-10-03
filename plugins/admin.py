import os
import asyncio
import shutil
import json

from datetime import datetime, timedelta, timezone
from sqlitedict import SqliteDict
from discord import Member, Role, TextChannel, Embed
from discord.ext import commands
from discord.ext.commands import Context

from core.discord_bot import DiscordBot
from core.db_tools import update_db
from core.time_tools import pretty_datetime, pretty_timedelta, time_parser

VERSION = "2.6b4"

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
    async def tempban_check(self):
        ts = datetime.now(tz=timezone.utc).timestamp()

        if len(self.tempban_db) <= 0:
            return

        for sid in self.tempban_db:
            if len(self.tempban_db[sid]) <= 0:
                continue

            for uid in self.tempban_db[sid]:
                info = self.tempban_db[sid][uid]

                if ts >= float(info["expires"]):
                    guild = self.bot.get_guild(int(sid))
                    await guild.unban(self.bot.get_user(uid))

                    del self.tempban_db[sid][uid]
                    update_db(self.sql_db, self.tempban_db, "temp_bans")
                    self.bot.log.info(
                        f"[ADMIN][TEMPBAN][REMOVE] {uid} in <{guild.name}>"
                    )

    async def warn_check(self):
        ts = datetime.now(tz=timezone.utc).timestamp()

        if len(self.warn_db) <= 0:
            return

        for sid in self.warn_db:
            if len(self.warn_db[sid]) <= 0:
                continue

            guild = self.bot.get_guild(int(sid))

            for uid in self.warn_db[sid]:
                for i, w in self.warn_db[sid][uid].items():
                    if ts >= float(w["expires"]):
                        del self.warn_db[sid][uid][i]
                        update_db(self.sql_db, self.warn_db, "warns")
                        self.bot.log.info(
                            f"[ADMIN][WARN][REMOVE] {uid}.{i} in <{guild.name}>"
                        )

    async def mute_check(self):
        ts = datetime.now(tz=timezone.utc).timestamp()

        if len(self.mute_db) <= 0:
            return

        for sid in self.mute_db:
            if len(self.mute_db[sid]) <= 0:
                continue

            for uid, info in self.mute_db[sid].items():
                if ts >= float(info["expires"]):
                    guild = self.bot.get_guild(int(sid))

                    try:
                        role = guild.get_role(int(self.db[sid]["mute_role"]))
                    # Delete the mute from the database if we're unable to get the mute role
                    except KeyError:
                        del self.mute_db[sid][uid]
                        break

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

        try:
            with open("config/config.json") as cfg:
                self.backup = json.load(cfg)["BackupDB"]
        except Exception as error:
            self.bot.log.error(f"Error loading from config file:\n    - {error}")

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
            color=0xff0000
        )
        embed.set_thumbnail(url=str(ctx.author.avatar_url))
        embed.add_field(name="Action", value=action, inline=False)
        embed.add_field(name="Target", value=tag)
        embed.add_field(name="Info", value=info)
        embed.set_footer(text=pretty_datetime(datetime.now()))

        await channel.send(embed=embed)

    @commands.group()
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
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

        embed = Embed(title="Admin Info", color=0x7289DA)
        embed.add_field(name="Log", value=log_status, inline=True)
        embed.add_field(name="Mute Role", value=mute_role, inline=True)
        embed.set_footer(text=pretty_datetime(datetime.now()))

        await ctx.send(embed=embed)

    @admin.command(name="log")
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def admin_log(self, ctx: Context, enabled: bool, channel: TextChannel = None):
        """Enable/disable to-channel logging and set the log channel.
        MUST HAVE SERVER ADMINISTRATOR PERMISSION
        """
        sid = str(ctx.guild.id)

        if sid not in self.db:
            self.db[sid] = {}

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
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def admin_role(self, ctx: Context, role: Role):
        """Set the mute role for the server.
        MUST HAVE SERVER ADMINISTRATOR PERMISSION
        """
        sid = str(ctx.guild.id)

        if sid not in self.db:
            self.db[sid] = {}

        self.db[sid]["mute_role"] = str(role.id)

        update_db(self.sql_db, self.db, "admin")

        await ctx.send(f":white_check_mark: Mute role set to: {role.name}.")

    @commands.command()
    @commands.has_permissions(kick_members=True)
    @commands.guild_only()
    async def kick(self, ctx: Context, target: Member, *, reason: str = None):
        """Kick a member from the server.
        Kick member permission required.
        """
        embed = await embed_builder("Kicked", target, reason)

        await target.send(embed=embed)

        await target.kick(reason=reason)

        tag = f"{target.name}#{target.discriminator}"
        await ctx.send(f":white_check_mark: Kicked {tag} for {reason}")
        await self.log_to_channel(ctx, target, reason)

    @commands.command(aliases=["sban"])
    @commands.has_permissions(ban_members=True)
    @commands.guild_only()
    async def softban(self, ctx: Context, target: Member, purge: int = 1,
                      *, reason: str = None):
        """Softban (kick and purge messages) a member from the server.
        Ban member permission required.
        """
        embed = await embed_builder("Kicked", target, reason)

        await target.send(embed=embed)

        await target.ban(reason=f"Softbanned: {reason}", delete_message_days=purge)
        await target.unban(reason="Softban removal")

        tag = f"{target.name}#{target.discriminator}"
        await ctx.send(f":white_check_mark: Softbanned {tag} for {reason}")
        await self.log_to_channel(ctx, target, reason)

    @commands.command()
    @commands.has_permissions(ban_members=True)
    @commands.guild_only()
    async def ban(self, ctx: Context, target: Member, purge: int = 7,
                  *, reason: str = None):
        """Ban a member from the server.
        Ban member permission required.
        """
        embed = await embed_builder("Permanently Banned", target, reason)

        await target.send(embed=embed)

        await target.ban(reason=reason, delete_message_days=purge)

        tag = f"{target.name}#{target.discriminator}"
        await ctx.send(f":white_check_mark: Banned {tag} for {reason}")
        await self.log_to_channel(ctx, target, reason)

    @commands.command(aliases=["tban"])
    @commands.has_permissions(ban_members=True)
    @commands.guild_only()
    async def tempban(self, ctx: Context, target: Member, length: int, span: str,
                      *, reason: str = None):
        """Temporarily ban a member from the server.
        For timing, plural and non-plural spans are accepted (Day, days, minutes, etc).
        Use "max" as the span for psuedo-permanence (10 years).
        Ban member permission required.
        """
        sid = str(ctx.guild.id)

        if sid not in self.tempban_db:
            self.tempban_db[sid] = {}

        # Get the current UTC time, a future time from time_parser, and the difference
        now = datetime.now(tz=timezone.utc)
        future = await time_parser(span, length, now)
        length = future - now

        embed = await embed_builder("Temporarily Banned", target, reason, length)

        await target.send(embed=embed)

        await target.ban(reason=reason, delete_message_days=0)

        self.tempban_db[sid][target.id] = {
            "issued_by": str(ctx.author.id),
            "reason": reason,
            "expires": str(future.timestamp())
        }

        update_db(self.sql_db, self.tempban_db, "temp_bans")

        tag = f"{target.name}#{target.discriminator}"
        await ctx.send(f":white_check_mark: Tempbanned {tag} for {reason}")
        await self.log_to_channel(ctx, target, reason)

    @commands.command()
    @commands.has_permissions(kick_members=True)
    @commands.guild_only()
    async def warn(self, ctx: Context, target: Member, length: int, span: str,
                   *, reason: str):
        """Warn a member.
        For timing, plural and non-plural spans are accepted (Day, days, minutes, etc).
        Use "max" as the span for psuedo-permanence (10 years).
        Kick member permission required.
        """
        sid = str(ctx.guild.id)
        uid = str(target.id)
        warn_count = 1

        if sid not in self.warn_db:
            self.warn_db[sid] = {}

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
        Kick member permission required to view other Members' warns
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

        # This is ugly but it's 4am and I don't care
        if (target is not ctx.author and not ctx.channel.permissions_for(
            ctx.author
        ).kick_members):
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

        for i, w in self.warn_db[sid][uid].items():
            now = datetime.now(tz=timezone.utc)
            then = datetime.fromtimestamp(float(w["expires"]), tz=timezone.utc)
            result = then - now

            expires = pretty_timedelta(result)

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
    @commands.has_permissions(kick_members=True)
    @commands.guild_only()
    async def warns_remove(self, ctx: Context, target: Member, number: int):
        """Remove a warning from a member.
        Kick member permission required.
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
    @commands.has_permissions(kick_members=True)
    @commands.guild_only()
    async def mute(self, ctx: Context, target: Member, length: int, span: str,
                   *, reason: str):
        """Set a member to the mute role.
        For timing, plural and non-plural spans are accepted (Day, days, minutes, etc).
        Use "max" as the span for psuedo-permanence (10 years).
        Kick member permission required.
        """
        sid = str(ctx.guild.id)
        uid = str(target.id)
        mute_role = None

        try:
            mute_role = ctx.guild.get_role(int(self.db[sid]["mute_role"]))
        except KeyError:
            await ctx.send(":anger: Server has no mute role set.")
            return

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

        await target.add_roles(mute_role)

        mute = {
            "issued_by": str(ctx.author.id),
            "reason": reason,
            "expires": str(future.timestamp())
        }

        self.mute_db[sid][uid] = mute

        update_db(self.sql_db, self.mute_db, "mutes")
        await self.log_to_channel(ctx, target, reason)

    @commands.command()
    @commands.has_permissions(kick_members=True)
    @commands.guild_only()
    async def unmute(self, ctx: Context, target: Member):
        """Unmute a member early.
        Kick member permission required.
        """
        sid = str(ctx.guild.id)
        uid = str(target.id)
        mute_role = None

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

        await target.remove_roles(mute_role)
        del self.mute_db[sid][uid]

        update_db(self.sql_db, self.mute_db, "mutes")

def setup(bot):
    bot.add_cog(Admin(bot))

def teardown(bot):
    bot.cogs["Admin"].sql_db.close()
    bot.remove_cog("Admin")
