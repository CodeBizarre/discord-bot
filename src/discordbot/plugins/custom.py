import os
import shutil
import json

from datetime import datetime
from sqlitedict import SqliteDict
from discord import Member, Embed, Message, ChannelType
from discord.ext import commands
from discord.ext.commands import Context

from discordbot.core.discord_bot import DiscordBot
from discordbot.core.db_tools import update_db
from discordbot.core.time_tools import pretty_datetime

VERSION = "1.2b4"

class CommandUser:
    """Class to avoid potential abuse from complex command scripting."""
    def __init__(self, member: Member):
        self.name = member.name
        self.discriminator = member.discriminator
        self.id = str(member.id)

        self.obj = {
            "id": self.id,
            "name": self.name,
            "discriminator": self.discriminator,
            "tag": f"{self.name}#{self.discriminator}",
            "mention": f"<@{self.id}>"
        }

class Custom(commands.Cog):
    def __init__(self, bot: DiscordBot):
        self.bot = bot
        self.name = "custom"
        self.version = VERSION
        self.backup = True

        try:
            with open("config/config.json") as cfg:
                self.backup = json.load(cfg)["BackupDB"]
        except Exception as error:
            self.bot.log.error(f"Error loading prefix from config file.\n    - {error}")

        db_file = "db/custom.sql"

        if os.path.exists(db_file) and self.backup:
            timestamp = pretty_datetime(datetime.now(), display="FILE")
            try:
                shutil.copyfile(db_file, f"db/backups/custom-{timestamp}.sql")
            except IOError as e:
                error_file = f"db/backups/custom-{timestamp}.sql"
                self.bot.log.error(f"Unable to create file {error_file}\n    - {e}")

        self.sql_db = SqliteDict(
            filename=db_file,
            tablename="custom",
            autocommit=True,
            encode=json.dumps,
            decode=json.loads
        )

        if "servers" not in self.sql_db:
            self.sql_db["servers"] = {}

        self.db = self.sql_db["servers"]

    def parse_command(self, member: Member, command: str) -> str:
        user = CommandUser(member)

        cmd = command.split(" ")
        for i, word in enumerate(cmd):
            # Argument is a replacer
            if word.startswith("!{") and word.endswith("}"):
                key = word[2:-1]
                try:
                    cmd[i] = user.obj[key]
                except KeyError:
                    # Ignore a formatting mistake
                    pass

        return " ".join(cmd)

    @commands.Cog.listener()
    async def on_message(self, msg: Message):
        if msg.author.id == self.bot.user.id: return
        if msg.channel.type == ChannelType.private: return

        sid = str(msg.guild.id)

        try:
            prefix = self.db[sid]["prefix"]
        except KeyError:
            prefix = None

        # Text command
        if prefix is not None and msg.content.startswith(prefix):
            command = msg.content.split(" ")[0].lstrip(prefix)

            try:
                cmd_result = self.db[sid]["text"][command]
                await msg.channel.send(cmd_result)
                return
            except KeyError:
                await msg.channel.send(":anger: That command doesn't exist.")
                return

        # Scripted responses
        try:
            complex_cmds = self.db[sid]["complex"]
        except KeyError:
            # Nothing to respond to
            return

        for trigger in complex_cmds:
            if (msg.content.startswith(trigger)):
                await msg.channel.send(
                    self.parse_command(msg.author, complex_cmds[trigger])
                )

    @commands.group()
    @commands.guild_only()
    async def custom(self, ctx: Context):
        """Create and manage custom commands on your server."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(self)

    @custom.command(name="prefix")
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def custom_prefix(self, ctx: Context, prefix: str = None):
        """Set your server's custom command prefix.
        Running the command without arguments will display the current prefix.
        Server administrator permission required.
        """
        sid = str(ctx.guild.id)

        if prefix is None:
            try:
                prefix = self.db[sid]["prefix"]
                await ctx.send(f"Current server prefix: `{prefix}`")
            except KeyError:
                await ctx.send(":anger: This server has no prefix")
            return

        try:
            if sid not in self.db:
                self.db[sid] = {}

            self.db[sid]["prefix"] = prefix
            update_db(self.sql_db, self.db, "servers")
            await ctx.send(":white_check_mark: Prefix updated!")
        except Exception as e:
            await ctx.send(f":anger: Something went wrong: {e}")

    @custom.group()
    @commands.guild_only()
    async def text(self, ctx: Context):
        """Create and remove simple text commands."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help("custom text")

    @text.command(name="list")
    @commands.guild_only()
    async def text_list(self, ctx: Context, page: int = 1):
        """See a paginated list of available text commands."""
        sid = str(ctx.guild.id)

        try:
            if "text" not in self.db[sid]:
                await ctx.send(":anger: This server has no text commands.")
            elif len(self.db[sid]["text"]) > 0:
                embed = Embed(title="Text Commands", color=0x7289DA)

                items = [(cmd, rsp) for cmd, rsp in self.db[sid]["text"].items()]

                start = (page - 1) * 6 if page > 1 else 0
                for i in items[start:start + 6]:
                    embed.add_field(name=i[0], value=i[1])

                remaining = (len(items)) - (start + 6)
                if remaining > 0:
                    prefix = self.bot.config_prefix
                    embed.add_field(
                        name=f"And {remaining} more. ",
                        value=f"Use `{prefix}custom text list {page + 1}`",
                        inline=False
                    )

                if len(embed.fields) > 0:
                    await ctx.send(embed=embed)
                else:
                    await ctx.send(":anger: No more commands.")
            else:
                await ctx.send(":anger: This server has no script responses.")
        except Exception as e:
            await ctx.send(f':anger: Something went wrong: {e}')

    @text.command(name="create", aliases=["c", "new", "make", "add"])
    @commands.has_permissions(manage_messages=True)
    @commands.guild_only()
    async def text_create(self, ctx: Context, name: str, *, text: str):
        """Create or update a new custom text command.
        Manage messages permission required.
        """
        sid = str(ctx.guild.id)

        if sid not in self.db:
            self.db[sid] = {
                "prefix": "_",
                "text": {}
            }
        elif "text" not in self.db[sid]:
            self.db[sid]["text"] = {}

        try:
            self.db[sid]["text"][name] = text
            update_db(self.sql_db, self.db, "servers")
            await ctx.send(f":white_check_mark: Command {name} added!")
        except Exception as e:
            await ctx.send(f":anger: Something went wrong: {e}")

    @text.command(name="remove", aliases=["r", "del", "delete"])
    @commands.has_permissions(manage_messages=True)
    @commands.guild_only()
    async def text_remove(self, ctx: Context, name: str):
        """Remove a custom text command.
        Manage messages permission required.
        """
        sid = str(ctx.guild.id)

        try:
            del self.db[sid]["text"][name]
            update_db(self.sql_db, self.db, "servers")
            await ctx.send(f":white_check_mark: Command `{name}` removed.")
        except KeyError:
            await ctx.send(
                f":anger: There is no command `{name}` registered on this server."
            )

    @custom.group()
    @commands.guild_only()
    async def script(self, ctx: Context):
        """Create and remove scripted replacer responses."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help("custom script")

    @script.command(name="list")
    @commands.guild_only()
    async def script_list(self, ctx: Context, page: int = 1):
        """See a paginated list of available script commands."""
        sid = str(ctx.guild.id)

        if sid not in self.db:
            await ctx.send(":anger: This server has no script responses.")
            return

        try:
            if "complex" not in self.db[sid]:
                await ctx.send(":anger: This server has no script responses.")
            elif len(self.db[sid]["complex"]) > 0:
                embed = Embed(title="Script Responses", color=0x7289DA)

                items = [(cmd, rsp) for cmd, rsp in self.db[sid]["complex"].items()]

                start = (page - 1) * 6 if page > 1 else 0
                for i in items[start:start + 6]:
                    embed.add_field(name=i[0], value=i[1])

                remaining = (len(items)) - (start + 6)
                if remaining > 0:
                    prefix = self.bot.config_prefix
                    embed.add_field(
                        name=f"And {remaining} more. ",
                        value=f"Use `{prefix}custom script list {page + 1}`",
                        inline=False
                    )

                if len(embed.fields) > 0:
                    await ctx.send(embed=embed)
                else:
                    await ctx.send(":anger: No more commands.")
            else:
                await ctx.send(":anger: This server has no script responses.")
        except Exception as e:
            await ctx.send(f":anger: Something went wrong: {e}")

    @script.command(name="create", aliases=["c", "new", "make", "add"])
    @commands.has_permissions(manage_messages=True)
    @commands.guild_only()
    async def script_create(self, ctx: Context, prefix: str, *, text: str):
        """Create or update a new script response.
        Manage messages permission required.
        """
        sid = str(ctx.guild.id)

        if sid not in self.db:
            self.db[sid] = { "complex": {} }
        elif "complex" not in self.db[sid]:
            self.db[sid]["complex"] = {}

        try:
            self.db[sid]["complex"][prefix] = text
            update_db(self.sql_db, self.db, "servers")
            await ctx.send(f":white_check_mark: Script response {prefix} added!")
        except Exception as e:
            await ctx.send(f":anger: Something went wrong: {e}")

    @script.command(name="remove", aliases=["r", "del", "delete"])
    @commands.has_permissions(manage_messages=True)
    @commands.guild_only()
    async def script_remove(self, ctx: Context, prefix: str):
        """Remove a custom response.
        Manage messages permission required.
        """
        sid = str(ctx.guild.id)

        try:
            del self.db[sid]["complex"][prefix]
            update_db(self.sql_db, self.db, "servers")
            await ctx.send(f":white_check_mark: Script response `{prefix}` removed.")
        except KeyError:
            await ctx.send(
                f":anger: There is no script response `{prefix}` "
                "registered on this server."
            )

def setup(bot):
    bot.add_cog(Custom(bot))

def teardown(bot):
    bot.cogs["Custom"].sql_db.close()
    bot.remove_cog("Groups")
