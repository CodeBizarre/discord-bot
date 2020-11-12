import os
import shutil
import asyncio
import json

from datetime import datetime, timezone
from sqlitedict import SqliteDict
from discord import Embed, PermissionOverwrite, Member
from discord.ext import commands
from discord.ext.commands import Context

from discordbot.core.discord_bot import DiscordBot
from discordbot.core.db_tools import update_db
from discordbot.core.time_tools import pretty_datetime

VERSION = "2.0b1"

class Groups(commands.Cog):
    """Dynamic group management plugin.

    Allows users to make and invite to temporary dynamic groups.
    """
    # Background task to check and remove old groups
    async def group_check(self):
        if len(self.db) <= 0:
            return

        for sid in self.db:
            if len(self.db[sid]) <= 0:
                del self.db[sid]
                continue

            for group, data in self.db[sid].items():
                info = data["info"]
                guild = self.bot.get_guild(int(sid))

                # Get the related channels and roles
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
                    # No message found, or there was some other error
                    self.bot.log.error(f"[ERROR][GROUPS]\n    - {e}")

                try:
                    last_datetime = last_message.created_at.replace(tzinfo=timezone.utc)
                    delta = datetime.now(tz=timezone.utc) - last_datetime
                    since_sent = int(delta.total_seconds())
                except Exception as e:
                    self.bot.log.error(f"[ERROR][GROUPS]\n    - {e}")
                    since_sent = 1801

                if not voice_channel.members and since_sent >= 1800:
                    try:
                        for chan in (text_channel, voice_channel, category, role):
                            await chan.delete(reason="Groups Plugin (Inactivity)")

                        del self.db[sid][group]
                        update_db(self.sql_db, self.db, "servers")
                    except Exception as e:
                        self.bot.log.error(f"[ERROR][GROUPS]:\n    - {e}")

    async def task_scheduler(self):
        while True:
            try:
                await self.group_check()
                await asyncio.sleep(60)
            except RuntimeError:
                # Database changed during iteration, this is expected when new entries
                # are added to the database, or old ones removed
                continue

    def __init__(self, bot: DiscordBot):
        self.bot = bot
        self.name = "groups"
        self.version = VERSION

        self.backup = True

        try:
            with open("config/config.json") as cfg:
                self.backup = json.load(cfg)["BackupDB"]
        except Exception as error:
            self.bot.log.error(f"Error loading prefix from config file.\n    - {error}")

        db_file = "db/groups.sql"

        if os.path.exists(db_file) and self.backup:
            timestamp = pretty_datetime(datetime.now(), display="FILE")
            try:
                shutil.copyfile(db_file, f"db/backups/groups-{timestamp}.sql")
            except IOError as e:
                error_file = f"db/backups/groups-{timestamp}.sql"
                self.bot.log.error(f"Unable to create file {error_file}\n    - {e}")

        self.sql_db = SqliteDict(
            filename=db_file,
            tablename="groups",
            autocommit=True,
            encode=json.dumps,
            decode=json.loads
        )

        if "servers" not in self.sql_db:
            self.sql_db["servers"] = {}

        self.db = self.sql_db["servers"]

        asyncio.create_task(self.task_scheduler())

    @commands.group(aliases=["group", "gr"])
    @commands.guild_only()
    async def groups(self, ctx: Context):
        """Base command to manage groups.

        Running the command without arguments will display the groups you currently
        have access to.
        """
        if ctx.invoked_subcommand is not None:
            return

        sid = str(ctx.guild.id)

        if sid in self.db and len(self.db[sid]) > 0:
            embed = Embed(title="Your groups:", color=0x7289DA)

            embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)

            for group, data in self.db[sid].items():
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
        if len(name) > 48:
            await ctx.send(":anger: Please use a name shorter than 48 characters.")
            return

        sid = str(ctx.guild.id)

        if sid not in self.db:
            self.db[sid] = {}

        # Try to make a role, text, and voice channel for the group
        try:
            role = await ctx.guild.create_role(
                name=name, reason="Groups plugin"
            )
            ow = {
                ctx.guild.default_role: PermissionOverwrite(read_messages=False),
                role: PermissionOverwrite(read_messages=True)
            }
            category = await ctx.guild.create_category(
                name=name,
                reason="Groups plugin",
                overwrites=ow
            )
            text = await ctx.guild.create_text_channel(
                name=name.lower(),
                reason="Groups plugin",
                category=category,
                topic=description
            )
            voice = await ctx.guild.create_voice_channel(
                name=name,
                reason="Groups plugin",
                category=category
            )

            self.db[sid][name] = {
                "info": {
                    "leader": str(ctx.author.id),
                    "description": description,
                    "category": str(category.id),
                    "text_channel": str(text.id),
                    "voice_channel": str(voice.id),
                    "role": str(role.id)
                }
            }

            update_db(self.sql_db, self.db, "servers")

            await ctx.author.add_roles(role, reason="Group created.")

        except Exception as e:
            await ctx.send(f":anger: Something went wrong: `{e}`")
            return

        await ctx.send(":white_check_mark: Group created!")
        await text.send(
            f"Welcome to your group {ctx.author.mention}! Try the `group invite` command!"
        )

    @groups.command(name="invite", aliases=["inv", "i", "add", "a"])
    @commands.guild_only()
    async def groups_invite(self, ctx: Context, target: Member, group: str):
        """Invite someone to your group!"""
        sid = str(ctx.guild.id)

        if sid not in self.db or group not in self.db[sid]:
            await ctx.send(
                f":anger: That group doesn't exist, try `group create {group}`!"
            )
            return

        role = ctx.guild.get_role(int(self.db[sid][group]["info"]["role"]))

        if role not in ctx.author.roles:
            await ctx.send(":anger: You are not part of that group!")
        else:
            if role in target.roles:
                await ctx.send(f":anger: That user is already a member of {group}!")
                return

            try:
                await target.add_roles(role, reason="Group invite")
                await ctx.send(
                    f":white_check_mark: Invited {target.name}#{target.discriminator}!"
                )

                group_channel = ctx.guild.get_channel(
                    int(self.db[sid][group]["info"]["text_channel"])
                )
                await group_channel.send(f"Welcome to {group} {target.mention}!")

            except Exception as e:
                await ctx.send(f":anger: Error during invite: {e}")

    @groups.command(name="leave", aliases=["exit", "l"])
    @commands.guild_only()
    async def groups_leave(self, ctx: Context, group: str):
        """Leave a group."""
        sid = str(ctx.guild.id)

        if sid not in self.db or group not in self.db[sid]:
            await ctx.send(":anger: That group doesn't exist!")
            return

        try:
            await ctx.author.remove_roles(int(self.db[sid][group]["info"]["role"]))
        except Exception as e:
            await ctx.send(f":anger: Error removing role: {e}")

    @groups.command(name="kick")
    @commands.guild_only()
    async def groups_kick(self, ctx: Context, target: Member):
        """Kick a member from your group.
        Must be the group leader, and the command must be issued from within
        the group channel.
        """
        sid = str(ctx.guild.id)

        try:
            info = self.db[sid][ctx.channel.category.name]["info"]
            role = ctx.guild.get_role(int(info["role"]))
        except KeyError:
            await ctx.send(f":anger: Unable to get info for {ctx.channel.category.name}")
            return

        if ctx.author.id != int(info["leader"]):
            await ctx.send(":anger: You are not the group leader!")
            return

        try:
            await target.remove_roles(role, reason=f"Groups-Plugin Kick [{ctx.author.id}]")
            await ctx.send(":white_check_mark: Member kicked!")
        except Exception as e:
            await ctx.send(f":anger: Something went wrong: {e}")

def setup(bot):
    bot.add_cog(Groups(bot))

def teardown(bot):
    bot.cogs["Groups"].sql_db.close()
    bot.remove_cog("Groups")
