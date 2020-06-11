import os
import shutil
import asyncio
import json

from datetime import datetime, timedelta, timezone
from sqlitedict import SqliteDict
from discord import Embed, PermissionOverwrite, Member
from discord.ext import commands
from discord.ext.commands import Context

from helpers import pretty_datetime, update_db

VERSION = "1.0b1"
GP = "Groups plugin."
IA = "Inactivity."

# Set up database
db_file = "db/groups.sql"
backup = True

# Check config and make a backup if required
try:
    with open("config/config.json") as cfg:
        backup = json.load(cfg)["BackupDB"]
except Exception as error:
    print(f"Error loading prefix from configuration file.\n    - {error}")

if os.path.exists(db_file) and backup:
    timestamp = pretty_datetime(datetime.now(), display="FILE")
    try:
        shutil.copyfile(db_file, f"db/backups/groups-{timestamp}.sql")
    except IOError as e:
        error_file = f"db/backups/groups-{timestamp}.sql"
        print(f"Unable to create file {error_file}\n    - {e}")

sql_db = SqliteDict(
    filename=db_file,
    tablename="groups",
    autocommit=True,
    encode=json.dumps,
    decode=json.loads
)

if "servers" not in sql_db:
    sql_db["servers"] = {}

db = sql_db["servers"]

async def group_check(bot: commands.Bot):
    # No servers registered
    if len(db) <= 0:
        return

    for sid in db:
        # No groups on this server
        if len(db[sid]) <= 0:
            continue

        # Each group in the server
        for group, data in db[sid].items():
            info = data["info"]
            guild = bot.get_guild(int(sid))

            # Instance the channels and roles
            category = guild.get_channel(int(info["category"]))
            text_channel = guild.get_channel(int(info["text_channel"]))
            voice_channel = guild.get_channel(int(info["voice_channel"]))
            role = guild.get_role(int(info["role"]))

            # Try to get the latest message from the text channel
            try:
                last_message = await text_channel.fetch_message(
                    text_channel.last_message_id
                )
            except Exception as e:
                # No message found, or there was some error
                print(f"[ERROR]\n    - {e}")
                break

            if last_message is None:
                return

            last_datetime = last_message.created_at.replace(tzinfo=timezone.utc)
            delta = datetime.now(tz=timezone.utc) - last_datetime

            since_sent = int(delta.total_seconds())

            if not voice_channel.members and since_sent >= 1800:
                try:
                    await voice_channel.delete(reason=IA)
                    await text_channel.delete(reason=IA)
                    await category.delete(reason=IA)
                    await role.delete(reason=IA)
                    db[sid].pop(group, f"Unable to remove {group} from database.")
                except Exception as e:
                    print(f"[ERROR]:\n    - {e}")

class Groups(commands.Cog):
    """Dynamic group management plugin.

    Allows users to make and invite to temporary dynamic groups.
    """
    # Background task scheduler
    async def task_scheduler(self):
        while True:
            try:
                await group_check(self.bot)
                await asyncio.sleep(60)
            except RuntimeError:
                # Database changed during iteration, this is expected when new entries
                # are added to the database, or old ones removed
                continue

    def __init__(self, bot):
        self.bot = bot
        self.name = "groups"
        asyncio.create_task(self.task_scheduler())

    @commands.group(aliases=["group", "gr"])
    @commands.guild_only()
    async def groups(self, ctx: Context):
        """Group related commands.

        Running the command without arguments will display the groups you currently
        have access to.
        """
        if ctx.invoked_subcommand is not None:
            return

        sid = str(ctx.guild.id)

        if sid in db and len(db[sid]) > 0:
            # Build an embed showing all groups the member is part of
            embed = Embed(title="Your groups:", color=0x7289DA)

            embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)

            for group, data in db[sid].items():
                info = data["info"]

                embed.add_field(name=group, value=info["description"])

            embed.set_footer(
                text="For more information use the `help groups` command."
            )

            await ctx.send(embed=embed)
        else:
            await ctx.send(":anger: You are not part of any groups.")

    @groups.command(name="create", aliases=["c", "cr", "new"])
    @commands.guild_only()
    async def groups_create(self, ctx: Context, name: str, *, description: str):
        """Create a group for you and your friends!
        Name must NOT include spaces!
        """
        sid = str(ctx.guild.id)

        if sid not in db:
            db[sid] = {}

        # Try to make a role, text, and voice channel for the group
        try:
            role = await ctx.guild.create_role(
                name=name, reason=GP
            )
            # Set overwrites for the category
            ow = {
                ctx.guild.default_role: PermissionOverwrite(read_messages=False),
                role: PermissionOverwrite(read_messages=True)
            }
            category = await ctx.guild.create_category(
                name=name,
                reason=GP,
                overwrites=ow
            )
            text = await ctx.guild.create_text_channel(
                name=name.lower(),
                reason=GP,
                category=category,
                topic=description
            )
            voice = await ctx.guild.create_voice_channel(
                name=name,
                reason=GP,
                category=category
            )

            db[sid] = {
                name: {
                    "info": {
                        "description": description,
                        "category": str(category.id),
                        "text_channel": str(text.id),
                        "voice_channel": str(voice.id),
                        "role": str(role.id)
                    }
                }
            }
            update_db(sql_db, db, "servers")

            await ctx.author.add_roles(role, reason="Group created.")

        except Exception as e:
            await ctx.send(f":anger: Something went wrong: `{e}`")
            return

        await ctx.send(":white_check_mark: Group created!")
        await text.send(
            f"Welcome to your group {ctx.author.mention}! Try the `group invite` command!"
        )

    @groups.command(name="invite", aliases=["inv", "i"])
    @commands.guild_only()
    async def groups_invite(self, ctx: Context, target: Member, group: str):
        """Invite someone to your group!"""
        sid = str(ctx.guild.id)

        if sid not in db:
            await ctx.send(":anger: This server has no groups, try `group create`!")
            return

        if group not in db[sid]:
            await ctx.send(
                f":anger: That group doesn't exist, try `group create {group}`!"
            )
            return

        # Get the group role
        role = ctx.guild.get_role(int(db[sid][group]["info"]["role"]))

        if role not in ctx.author.roles:
            await ctx.send(":anger: You are not part of that group!")
        else:
            if role in target.roles:
                await ctx.send(f":anger: That user is already a member of {group}!")
                return

            try:
                # Add the role to the target, and send confirmation in both chanels
                await target.add_roles(role, reason="Group invite")
                await ctx.send(
                    f":white_check_mark: Invited {target.name}#{target.discriminator}!"
                )

                group_channel = ctx.guild.get_channel(
                    int(db[sid][group]["info"]["text_channel"])
                )
                await group_channel.send(f"Welcome to {group} {target.mention}!")

            except Exception as e:
                await ctx.send(f":anger: Error during invite: {e}")

def setup(bot):
    bot.add_cog(Groups(bot))
