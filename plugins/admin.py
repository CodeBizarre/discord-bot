import asyncio
import os
import shutil
import json

from sqlitedict import SqliteDict
from datetime import datetime, timedelta, timezone
from discord import Member, Role, TextChannel, Embed
from discord.ext import commands
from discord.ext.commands import Context

from main import is_level
from helpers import update_db, pretty_datetime, pretty_timedelta

VERSION = "2.0.0b1"

# Set up the database
db_file = "db/admin.sql"
backup = True

try:
    with open("config/config.json") as cfg:
        backup = json.load(cfg)["BackupDB"]
except Exception as error:
    print(f"Error loading prefix from configuration file.\n    - {error}")

if os.path.exists(db_file) and backup:
    timestamp = pretty_datetime(datetime.now(), display="FILE")
    try:
        shutil.copyfile(db_file, f"db/backups/roles-{timestamp}.sql")
    except IOError as e:
        print(
            f"""
            Unable to create file db/backups/roles-{timestamp}.sql:\n
            {e}
            """
        )

sql_db = SqliteDict(
    filename=db_file,
    tablename="admin",
    autocommit=True,
    encode=json.dumps,
    decode=json.loads
)

if "admin" not in sql_db:
    sql_db["admin"] = {}

if "temp_bans" not in sql_db:
    sql_db["temp_bans"] = {}

if "warns" not in sql_db:
    sql_db["warns"] = {}

if "mutes" not in sql_db:
    sql_db["mutes"] = {}

db = sql_db["admin"]
tempban_db = sql_db["temp_bans"]
warn_db = sql_db["warns"]
mute_db = sql_db["mutes"]

# Parser for basic time strings ex 1d 12h 15m etc
async def time_parser(span: str, length: int, dt: datetime) -> datetime:
    switcher = {
        "seconds": lambda: timedelta(seconds=length),
        "minutes": lambda: timedelta(minutes=length),
        "hours": lambda: timedelta(hours=length),
        "days": lambda: timedelta(days=length),
        "weeks": lambda: timedelta(weeks=length),
        "months": lambda: timedelta(days=length*30),
        "years": lambda: timedelta(days=length*365)
    }

    if span in switcher:
        # Grab the function from the switcher
        case = switcher[span]
    elif span + "s" in switcher:
        case = switcher[span + "s"]

    # Calculate and return the time in the future
    future = dt + case()
    return future

async def tempban_check(bot: commands.Bot):
    ts = datetime.now(tz=timezone.utc).timestamp()

    if len(tempban_db) <= 0:
        return

    for sid in tempban_db:
        if len(tempban_db[sid]) <= 0:
            continue

        for uid in tempban_db[sid]:
            info = tempban_db[sid][uid]

            if float(info["expires"]) >= ts:
                guild = bot.get_guild(int(sid))
                await guild.unban(bot.get_user(uid))
                del tempban_db[sid][uid]
                update_db(sql_db, tempban_db, "temp_bans")

async def warn_check():
    ts = datetime.now(tz=timezone.utc).timestamp()

    if len(warn_db) <= 0:
        return

    for sid in warn_db:
        if len(warn_db[sid]) <= 0:
            continue

        for uid in warn_db[sid]:
            for i, w in warn_db[sid][uid].items():
                if ts >= float(w["expires"]):
                    del warn_db[sid][uid][i]
                    update_db(sql_db, warn_db, "warns")

async def mute_check(bot: commands.Bot):
    ts = datetime.now(tz=timezone.utc).timestamp()

    if len(mute_db) <= 0:
        return

    for sid in mute_db:
        if len(mute_db[sid]) <= 0:
            continue

        for i, uid in mute_db[sid].items():
            if ts >= float(uid["expires"]):
                # FIXME: This is probably broken in some way?
                # The break statements mean that a mute could get stuck
                # Oh well it's 6am I'll fix it later
                guild = bot.get_guild(int(sid))
                try:
                    role = guild.get_role(int(db[sid]["mute_role"]))
                except KeyError:
                    break
                target = guild.get_member(int(i))
                if role in target.roles:
                    await target.remove_roles(role, reason="Auto mute remove.")
                    await target.send(f"You have been unmuted in {guild.name}.")
                else:
                    break
                del mute_db[sid][uid]
                update_db(sql_db, mute_db, "mutes")

# TODO: Messages along with log_to_channel (emoji update?)
class Admin(commands.Cog):
    """General purpose administration plugin.

    Features warning, kicking, banning, soft bans, timed bans, and message purging.
    """
    # Background task scheduling system
    async def task_scheduler(self):
        while True:
            try:
                await tempban_check(self.bot)
                await warn_check()
                await mute_check(self.bot)
                await asyncio.sleep(60)
            except RuntimeError:
                # Database changed during iteration
                # This is expected when new bans/warns are added
                continue

    def __init__(self, bot):
        self.bot = bot
        self.name = "admin"
        asyncio.create_task(self.task_scheduler())

    # Send an embed-formatted log of an event to a channel
    async def log_to_channel(self, ctx: Context, target: Member, info: str = None):
        sid = str(ctx.guild.id)
        channel = None
        action = ctx.message.content

        if sid in db:
            channel = ctx.guild.get_channel(int(db[sid]["log_channel"]))
        else:
            channel = ctx.channel

        if info is None:
            info = "No extra information"

        tag = f"{target.name}#{target.discriminator} ({target.id})"

        embed = Embed(title=action, color=0xff0000)
        embed.add_field(name=ctx.command.name, value=tag, inline=True)
        embed.add_field(name="Info", value=info)
        embed.set_footer(text=pretty_datetime(datetime.now()))

        await channel.send(embed=embed)

    @commands.group()
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def admin(self, ctx: Context):
        """Base command for server administrators.

        Run without arguments to view current server settings and stats.
        """
        if ctx.invoked_subcommand is None:
            sid = str(ctx.guild.id)

            log_status = None
            mute_role = None
            try:
                channel = self.bot.get_channel(int(db[sid]["log_channel"]))
                log_status = f"{db[sid]['log']}, {channel.mention}"
            except KeyError:
                log_status = "Not set up"
            try:
                role = ctx.guild.get_role(int(db[sid]["mute_role"]))
                mute_role = role.name
            except KeyError:
                mute_role = "Not set up"

            embed = Embed(title="Admin Info", color=0xffffff)
            embed.add_field(name="Log", value=log_status, inline=True)
            embed.add_field(name="Mute Role", value=mute_role, inline=True)
            embed.set_footer(text=pretty_datetime(datetime.now()))

            await ctx.send(embed=embed)

    @admin.command(name="log")
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def admin_set(self, ctx: Context, enabled: bool, channel: TextChannel = None):
        """Set and enable/disable event logging channel."""
        sid = str(ctx.guild.id)

        if sid not in db:
            db[sid] = {}

        db[sid]["log"] = enabled

        if channel is not None:
            db[sid]["log_channel"] = str(channel.id)
        else:
            if "log_channel" not in db[sid]:
                db[sid]["log_channel"] = str(ctx.message.channel.id)
            channel = ctx.message.channel

        update_db(sql_db, db, "admin")

        await ctx.send(f"Log setting: {enabled}\nlog channel: {channel.mention}")

    @admin.command(name="role")
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def admin_role(self, ctx: Context, role: Role):
        """Set the mute role for the server."""
        sid = str(ctx.guild.id)

        if sid not in db:
            db[sid] = {}

        db[sid]["mute_role"] = str(role.id)

        update_db(sql_db, db, "admin")

        await ctx.send(f"Mute role set to: {role.name}.")

    @commands.command()
    @is_level(6)
    async def kick(self, ctx: Context, target: Member, *, reason: str = None):
        """Kick a member from the server."""
        await target.send(
            "You have been kicked from {0} for {1}\nYou may rejoin.".format(
                ctx.guild.name,
                reason
            )
        )
        await target.kick(reason=reason)
        await self.log_to_channel(ctx, target, reason)

    @commands.command(aliases=["sban"])
    @is_level(7)
    async def softban(
        self,
        ctx: Context,
        target: Member,
        purge: int = 1,
        *, reason: str = None):
        """Softban (kick and purge messages) a member."""
        await target.send(
            "You have been softbanned from {0} for {1}\nYou may rejoin.".format(
                ctx.guild.name,
                reason
            )
        )
        await target.ban(reason=f"Softbanned: {reason}", delete_message_days=purge)
        await target.unban(reason="Softban removal")
        await self.log_to_channel(ctx, target, reason)

    @commands.command()
    @is_level(8)
    async def ban(
        self,
        ctx: Context,
        target: Member,
        purge: int = 7,
        *, reason: str = None):
        """Ban a member from the server."""
        await target.send(
            "You have been permanently banned from {0} for {1}".format(
                ctx.guild.name,
                reason
            )
        )
        await target.ban(reason=reason, delete_message_days=purge)
        await self.log_to_channel(ctx, target, reason)

    @commands.command(aliases=["tban"])
    @is_level(8)
    async def tempban(
        self,
        ctx: Context,
        target: Member,
        length: int,
        span: str,
        purge: int = 1,
        *, reason: str = None):
        """Temporarily ban a member from the server."""
        sid = str(ctx.guild.id)

        if sid not in tempban_db:
            tempban_db[sid] = {}

        now = datetime.now(tz=timezone.utc)
        future = await time_parser(span, length, now)
        length = future - now
        readable_time = pretty_timedelta(length)

        await target.send(
            "You have been temporarily banned for {0} from {1} for {2}".format(
                readable_time,
                ctx.guild.name,
                reason
            )
        )
        await target.ban(reason=reason, delete_message_days=purge)
        tempban_db[sid][target.id] = {
            "issued_by": str(ctx.author.id),
            "reason": reason,
            "expires": str(future.timestamp())
        }
        update_db(sql_db, tempban_db, "temp_bans")
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
        await ctx.channel.purge(limit=count, check=lambda m: m.author == ctx.author)
        await self.log_to_channel(ctx, ctx.author)

    @purge.command(name="bot")
    @commands.guild_only()
    @is_level(5)
    async def purge_bot(self, ctx: Context, count: int = 10):
        """Purge messages sent by the bot."""
        await ctx.channel.purge(limit=count, check=lambda m: m.author.id == ctx.bot.id)
        await self.log_to_channel(ctx, ctx.author)

    @purge.command(name="all", aliases=["everyone"])
    @commands.guild_only()
    @is_level(5)
    async def purge_all(self, ctx: Context, count: int = 10):
        """Purge all messages."""
        await ctx.channel.purge(limit=count)
        await self.log_to_channel(ctx, ctx.author)

    @purge.command(name="member", aliases=["user"])
    @commands.guild_only()
    @is_level(5)
    async def purge_member(self, ctx: Context, member: Member, count: int = 10):
        """Purge messages from a specific user."""
        await ctx.channel.purge(limit=count, check=lambda m: m.author == member)
        await self.log_to_channel(ctx, member)

    @purge.command(name="role", aliases=["group"])
    @commands.guild_only()
    @is_level(5)
    async def purge_group(self, ctx: Context, role: Role, count: int = 10):
        """Purge messages from a specific role."""
        await ctx.channel.purge(limit=count, check=lambda m: role in m.author.roles)
        await self.log_to_channel(ctx, ctx.author)

    @commands.command()
    @commands.guild_only()
    @is_level(4)
    async def warn(
        self,
        ctx: Context,
        target: Member,
        length: int,
        span: str,
        *, reason: str):
        """Warn a member."""
        sid = str(ctx.guild.id)
        uid = str(target.id)
        warn_count = 1

        if sid not in warn_db:
            warn_db[sid] = {}

        if uid in warn_db[sid]:
            for w in warn_db[sid][uid]:
                warn_count += 1

        now = datetime.now(tz=timezone.utc)
        future = await time_parser(span, length, now)
        length = future - now
        readable_time = pretty_timedelta(length)

        await target.send(
            "You have been warned for {0} in {1}. This warning will epxire in {2}".format(
                reason,
                ctx.guild.name,
                readable_time
            )
        )
        await target.send(f"This is warning #{warn_count}.")
        await ctx.send(f"Warning {warn_count} issued to {target.name} for {reason}")

        if uid not in warn_db[sid]:
            warn_db[sid][uid] = {}

        warning = {
            "issued_by": str(ctx.author.id),
            "reason": reason,
            "expires": str(future.timestamp())
        }
        warn_db[sid][uid][str(warn_count)] = warning

        update_db(sql_db, warn_db, "warns")
        await self.log_to_channel(ctx, target, reason)

    @commands.command()
    @commands.guild_only()
    @is_level(4)
    async def warns(self, ctx: Context, member: Member):
        """List all active warns of a member."""
        sid = str(ctx.guild.id)
        uid = str(member.id)

        if sid not in warn_db:
            await ctx.send("Server has no warns.")
            return

        if uid not in warn_db[sid]:
            await ctx.send("Member has no warns.")
            return

        embed = Embed(
            title=f"{member.name}#{member.discriminator}'s Warns",
            color=0xff0000
        )

        warn_count = len(warn_db[sid][uid])

        embed.add_field(
            name="Total warns",
            value=str(warn_count),
            inline=False
        )

        for i, w in warn_db[sid][uid].items():
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

    @commands.command()
    @commands.guild_only()
    @is_level(4)
    async def mute(
        self,
        ctx: Context,
        target: Member,
        length: int,
        span: str,
        *, reason: str):
        """Mute a user."""
        sid = str(ctx.guild.id)
        uid = str(target.id)

        if sid not in mute_db:
            mute_db[sid] = {}

        now = datetime.now(tz=timezone.utc)
        future = await time_parser(span, length, now)
        length = future - now
        readable_time = pretty_timedelta(length)

        await target.send(
            "You have been muted for {0} in {1} for {2}".format(
                reason,
                ctx.guild.name,
                readable_time
            )
        )
        await ctx.send(f"{target.name} muted for {reason}, expires in {readable_time}")

        mute = {
            "issued_by": str(ctx.author.id),
            "reason": reason,
            "expires": str(future.timestamp())
        }

        mute_db[sid][uid] = mute

        update_db(sql_db, mute_db, "mutes")
        await self.log_to_channel(ctx, target, reason)

    @commands.command()
    @commands.guild_only()
    @is_level(4)
    async def unmute(self, ctx: Context, target: Member):
        """Unmute a user early."""
        sid = str(ctx.guild.id)
        uid = str(target.id)

        if sid not in mute_db:
            await ctx.send("This server has no mutes.")
            return

        if uid not in mute_db[sid]:
            await ctx.send("This member is not muted.")
            return

        await target.send(f"You have been unmuted in {ctx.guild.name}.")
        await ctx.send(f"Unmuted {target.name}.")

        del mute_db[sid][uid]

        update_db(sql_db, mute_db, "mutes")

def setup(bot):
    bot.add_cog(Admin(bot))
