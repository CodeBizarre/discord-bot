import os
import asyncio
import shutil
import json

from datetime import datetime, timedelta, timezone
from sqlitedict import SqliteDict
from discord import Member, Role, TextChannel, Embed
from discord.ext import commands
from discord.ext.commands import Context

from main import is_level, get_account
from helpers import update_db, pretty_datetime, pretty_timedelta

VERSION = "2.1b1"

# Set up the database
db_file = "db/admin.sql"
backup = True

# Check the config and make any required backups
try:
    with open("config/config.json") as cfg:
        backup = json.load(cfg)["BackupDB"]
except Exception as error:
    print(f"Error loading prefix from configuration file.\n    - {error}")

if os.path.exists(db_file) and backup:
    timestamp = pretty_datetime(datetime.now(), display="FILE")
    try:
        shutil.copyfile(db_file, f"db/backups/admin-{timestamp}.sql")
    except IOError as e:
        error_file = f"db/backups/admin-{timestamp}.sql"
        log.error(f"Unable to create file {error_file}\n    - {e}")

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

# Parser to convert length/span combos into a future datetime object
async def time_parser(span: str, length: int, dt: datetime) -> datetime:
    # Psuedo switch/case to return a lambda function for the timedelta
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

# Coroutine to run in a background thread to check if tempbans are expired
async def tempban_check(bot: commands.Bot):
    ts = datetime.now(tz=timezone.utc).timestamp()

    # No servers registered
    if len(tempban_db) <= 0:
        return

    for sid in tempban_db:
        # No tempbans in this server
        if len(tempban_db[sid]) <= 0:
            continue

        # Each tempban in the server
        for uid in tempban_db[sid]:
            info = tempban_db[sid][uid]

            if ts >= float(info["expires"]):
                guild = bot.get_guild(int(sid))
                await guild.unban(bot.get_user(uid))

                del tempban_db[sid][uid]
                update_db(sql_db, tempban_db, "temp_bans")
                print(f"[ADMIN][TEMPBAN][REMOVE] {target.id} in <{guild.name}>")

# Coroutine to run in a background thread to check if warns are expired
async def warn_check():
    ts = datetime.now(tz=timezone.utc).timestamp()

    # No servers registered
    if len(warn_db) <= 0:
        return

    for sid in warn_db:
        # No warns in the server
        if len(warn_db[sid]) <= 0:
            continue

        guild = bot.get_guild(int(sid))

        # Each warn in the server
        for uid in warn_db[sid]:
            for i, w in warn_db[sid][uid].items():
                if ts >= float(w["expires"]):
                    del warn_db[sid][uid][i]
                    update_db(sql_db, warn_db, "warns")
                    print(f"[ADMIN][WARN][REMOVE] {uid}.{i} in <{guild.name}>")

# Coroutine to run in a background thread to check if mutes are expired
async def mute_check(bot: commands.Bot):
    ts = datetime.now(tz=timezone.utc).timestamp()

    # No servers registered
    if len(mute_db) <= 0:
        return

    for sid in mute_db:
        # No mutes in this server
        if len(mute_db[sid]) <= 0:
            continue

    # Each mute in the server
    for uid, info in mute_db[sid].items():
        if ts >= float(info["expires"]):
            guild = bot.get_guild(int(sid))

            # Get the mute role
            try:
                role = guild.get_role(int(db[sid]["mute_role"]))
            # Delete the mute from the database if we're unable to get the mute role
            except KeyError:
                del mute_db[sid][uid]
                break

            # Else get the member and remove the mute role
            target = guild.get_member(int(uid))

            if role in target.roles:
                await target.remove_roles(role, reason="Auto mute remove.")
                await target.send(
                    f":speaking_head: Your mute in {guild.name} has expired."
                )
            else:
                del mute_db[sid][uid]
                break

            del mute_db[sid][uid]
            update_db(sql_db, mute_db, "mutes")
            print(f"[ADMIN][MUTE][REMOVE] {target.id} in <{guild.name}>")

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
                # This is expected when new bans/warns/mutes are added
                continue

    def __init__(self, bot):
        self.bot = bot
        self.name = "admin"
        asyncio.create_task(self.task_scheduler())

    # Send an embed-formatted log of an event to a channel
    async def log_to_channel(self, ctx: Context, target: Member, info: str = None):
        sid = str(ctx.guild.id)
        channel = None
        enabled = True
        action = ctx.message.content

        # Try and get the config values for the server
        if sid in db:
            try:
                channel = ctx.guild.get_channel(int(db[sid]["log_channel"]))
            except KeyError:
                channel = None
            try:
                enabled = db[sid]["log"]
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

        Run without arguments to view current server settings.
        MUST HAVE SERVER ADMINISTRATOR PERMISSION
        """
        if ctx.invoked_subcommand is None:
            sid = str(ctx.guild.id)
            log_status = None
            mute_role = None

            # Get the server's config values
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
        """Set to-channel logging to <Channel> (TextChannel) to <Enabled>.
        MUST HAVE SERVER ADMINISTRATOR PERMISSION
        """
        sid = str(ctx.guild.id)

        # Initialize the server in the database if required
        if sid not in db:
            db[sid] = {}

        # Set the config values based on user input (or lack thereof for log channel)
        db[sid]["log"] = enabled

        if channel is not None:
            db[sid]["log_channel"] = str(channel.id)
        else:
            if "log_channel" not in db[sid]:
                db[sid]["log_channel"] = str(ctx.message.channel.id)
            channel = ctx.message.channel

        update_db(sql_db, db, "admin")

        embed = Embed(title="Log Settings", color=0xff0000)
        embed.add_field(name="Enabled", value=str(enabled))
        embed.add_field(name="Log Channel", value=channel.mention)

        await ctx.send(embed=embed)

    @admin.command(name="role")
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def admin_role(self, ctx: Context, role: Role):
        """Set the mute <Role> (Role) for the server.
        MUST HAVE SERVER ADMINISTRATOR PERMISSION
        """
        sid = str(ctx.guild.id)

        # Initialize the server in the database if required
        if sid not in db:
            db[sid] = {}

        # Set the mute role
        db[sid]["mute_role"] = str(role.id)

        update_db(sql_db, db, "admin")

        await ctx.send(f":white_check_mark: Mute role set to: {role.name}.")

    @commands.command()
    @is_level(6)
    async def kick(self, ctx: Context, target: Member, *, reason: str = None):
        """Kick <Target> (Member) from the server for [Reason].
        Level 6 required
        """
        embed = await embed_builder("Kicked", target, reason)

        await target.send(embed=embed)

        await target.kick(reason=reason)
        await self.log_to_channel(ctx, target, reason)

    @commands.command(aliases=["sban"])
    @is_level(7)
    async def softban(self, ctx: Context, target: Member, purge: int = 1,
        *, reason: str = None):
        """Softban (kick and purge messages) <Target> (Member) from the server for
        [Reason] and remove all of their messages from the past [Purge] days.
        Level 7 required
        """
        embed = await embed_builder("Kicked", target, reason)

        await target.send(embed=embed)

        await target.ban(reason=f"Softbanned: {reason}", delete_message_days=purge)
        await target.unban(reason="Softban removal")

        await self.log_to_channel(ctx, target, reason)

    @commands.command()
    @is_level(8)
    async def ban(self, ctx: Context, target: Member, purge: int = 7,
        *, reason: str = None):
        """Ban <Target> (Member) from the server for [Reason] and remove all of their
        messages from the past [Purge] days.
        Level 8 required
        """
        embed = await embed_builder("Permanently Banned", target, reason)

        await target.send(embed=embed)

        await target.ban(reason=reason, delete_message_days=purge)

        await self.log_to_channel(ctx, target, reason)

    @commands.command(aliases=["tban"])
    @is_level(8)
    async def tempban(self, ctx: Context, target: Member, length: int, span: str,
        *, reason: str = None):
        """Temporarily ban <Target> (Member) from the server for [Reason] lasting
        <Length> <Span>(s) (Example: 10 days, plural and non-plural spans accepted).
        Level 8 required
        """
        sid = str(ctx.guild.id)

        # Initialize the server in the tempban database if required
        if sid not in tempban_db:
            tempban_db[sid] = {}

        # Get the current UTC time, a future time from time_parser, and the difference
        now = datetime.now(tz=timezone.utc)
        future = await time_parser(span, length, now)
        length = future - now

        embed = await embed_builder("Temporarily Banned", target, reason, length)

        await target.send(embed=embed)

        await target.ban(reason=reason, delete_message_days=0)

        # Add the tempban to the database
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
        """Purge messages from yourself in the last <Count> messages."""
        await ctx.channel.purge(limit=count, check=lambda m: m.author == ctx.author)
        await self.log_to_channel(ctx, ctx.author)

    @purge.command(name="bot")
    @commands.guild_only()
    @is_level(5)
    async def purge_bot(self, ctx: Context, count: int = 10):
        """Purge messages sent by the bot in the last <Count> messages.
        Level 5 required
        """
        await ctx.channel.purge(limit=count, check=lambda m: m.author.id == ctx.bot.id)
        await self.log_to_channel(ctx, ctx.author)

    @purge.command(name="all", aliases=["everyone"])
    @commands.guild_only()
    @is_level(5)
    async def purge_all(self, ctx: Context, count: int = 10):
        """Purge all of the last <Count> messages.
        Level 5 required
        """
        await ctx.channel.purge(limit=count)
        await self.log_to_channel(ctx, ctx.author)

    @purge.command(name="member", aliases=["user"])
    @commands.guild_only()
    @is_level(5)
    async def purge_member(self, ctx: Context, member: Member, count: int = 10):
        """Purge messages from <Member> (Member) in the last <Count> messages.
        Level 5 required
        """
        await ctx.channel.purge(limit=count, check=lambda m: m.author == member)
        await self.log_to_channel(ctx, member)

    @purge.command(name="role", aliases=["group"])
    @commands.guild_only()
    @is_level(5)
    async def purge_group(self, ctx: Context, role: Role, count: int = 10):
        """Purge messages from <Role> (Role) in the last <Count> messages.
        Level 5 required
        """
        await ctx.channel.purge(limit=count, check=lambda m: role in m.author.roles)
        await self.log_to_channel(ctx, ctx.author)

    @commands.command()
    @commands.guild_only()
    @is_level(4)
    async def warn(self, ctx: Context, target: Member, length: int, span: str,
        *, reason: str):
        """Warn <Target> (Member) for [Reason] and set it to expire in <Length> <Span>(s).
        (Example: 10 days, plural and non-plural spans accepted).
        Level 4 required
        """
        sid = str(ctx.guild.id)
        uid = str(target.id)
        warn_count = 1

        # Initialize the server in the warn database if required
        if sid not in warn_db:
            warn_db[sid] = {}

        # Add 1 to the amount of warns the user may already have
        if uid in warn_db[sid]:
            for w in warn_db[sid][uid]:
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
    async def warns(self, ctx: Context, member: Member = None):
        """List all active warns of yourself or [Member] (Member).
        Invoke without argument to view your own warns.
        Level 4 required to view other Members' warns
        """
        sid = str(ctx.guild.id)

        if member is None:
            member = ctx.author

        uid = str(member.id)

        if member is not ctx.author:
            level = get_account(ctx.guild, ctx.author)
            if level < 4:
                await ctx.send(":anger: Must be level 4 to view other users' warns.")
                return

        if sid not in warn_db:
            await ctx.send(":anger: Server has no warns.")
            return

        if uid not in warn_db[sid]:
            await ctx.send(":anger: Member has no warns.")
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

        # Build the fields of the embed by iterating through a user's warns
        for i, w in warn_db[sid][uid].items():
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

    @commands.command()
    @commands.guild_only()
    @is_level(4)
    async def mute(self, ctx: Context, target: Member, length: int, span: str,
        *, reason: str):
        """Set <Target> (Member) to the mute role for [Reason] expiring in
        <Length> <Span>(s). (Example: 10 days, plural and non-plural spans accepted).
        Level 4 required
        """
        sid = str(ctx.guild.id)
        uid = str(target.id)
        mute_role = None

        # Try to get the mute role from the server
        try:
            mute_role = ctx.guild.get_role(int(db[sid]["mute_role"]))
        except KeyError:
            await ctx.send(":anger: Server has no mute role set.")
            return

        # Initialize the server in the mute database if required
        if sid not in mute_db:
            mute_db[sid] = {}

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

        mute_db[sid][uid] = mute

        update_db(sql_db, mute_db, "mutes")
        await self.log_to_channel(ctx, target, reason)

    @commands.command()
    @commands.guild_only()
    @is_level(4)
    async def unmute(self, ctx: Context, target: Member):
        """Unmute <Target> (Member) early.
        Level 4 required
        """
        sid = str(ctx.guild.id)
        uid = str(target.id)
        mute_role = None

        # Try to get the mute role from the server
        try:
            mute_role = ctx.guild.get_role(int(db[sid]["mute_role"]))
        except KeyError:
            await ctx.send(":anger: This server has no mute role set.")
            return

        if sid not in mute_db:
            await ctx.send(":anger: This server has no mutes.")
            return

        if uid not in mute_db[sid]:
            await ctx.send(":anger: This member is not muted.")
            return

        await target.send(f":speaking_head: You have been unmuted in {ctx.guild.name}.")
        await ctx.send(f":speaking_head: Unmuted {target.name}.")

        # Remove the mute role and delete the entry from the database
        await target.remove_roles(mute_role)
        del mute_db[sid][uid]

        update_db(sql_db, mute_db, "mutes")

def setup(bot):
    bot.add_cog(Admin(bot))
