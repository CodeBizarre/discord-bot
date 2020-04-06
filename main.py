# Aurexine 2020
## IMPORTS
import os
import shutil
import json

from datetime import datetime
from sqlitedict import SqliteDict
from discord import Guild, Message, User, Member, Embed
from discord.ext import commands
from discord.ext.commands import Context

from helpers import *

VERSION = "2.1.1b1"

## FILESYSTEM
# Get the filesystem in ship-shape
try:
    # Generate a default config if it doesn't exist
    if not os.path.exists("config") or not os.path.exists("config/config.json"):
        os.makedirs("config")
        default_config = {
            "Database": "database.sql",
            "BackupDB": True,
            "Botmasters": ["Discord user IDS", "Go here WITH QUOTES"],
            "Prefix": "~",
            "Token": "Bot token goes here",
            "CommandsOnEdit": True,
            "LogFile": "bot.log",
            "LogMessages": True,
            "LogEdits": True,
            "LogDeletes": True,
            "LogCommands": True
        }
        with open("config/config.json", "w") as gen:
            gen.write(json.dumps(default_config, indent=4))

    if not os.path.exists("db"):
        os.makedirs("db")

    if not os.path.exists("db/backups"):
        os.makedirs("db/backups")

    if not os.path.exists("plugins"):
        os.makedirs("plugins")
except IOError as e:
    print(e)
    exit()

## CLASSES
class DiscordBot:
    """Data class to hold bot and config information."""
    def __init__(self, description):
        # Discord library initializations
        self.description = description
        self.bot = None
        self.app_info = None
        try:
            with open("config/config.json") as cfg:
                config = json.load(cfg)
                self.database       = config["Database"]
                self.backup_db      = config["BackupDB"]
                self.config_prefix  = config["Prefix"]
                self.config_token   = config["Token"]
                self.cmd_on_edit    = config["CommandsOnEdit"]
                self.log_file       = config["LogFile"]
                self.log_messages   = config["LogMessages"]
                self.log_edits      = config["LogEdits"]
                self.log_deletes    = config["LogDeletes"]
                self.log_commands   = config["LogCommands"]
                self.botmasters     = config["Botmasters"]
        except IOError as e:
            print(e)
            exit()
        # Non-config initializations
        self.blacklist = []
        self.plugins = []
        self.servers = {}
        self.accounts = {}
        self.first_launch = True

    # Return current information
    def mission_control(self) -> str:
        if self.bot is None:
            return "Bot not initialized."
        else:
            server_names = [i.name for i in self.bot.guilds]
            lines = []
            lines.append(f"[------------------------STATUS------------------------]")
            lines.append("Source: https://github.com/Aurexine/discord-bot")
            lines.append(f"Time: {datetime.now()}")
            lines.append(f"Version: {VERSION}")
            lines.append(f"Logged in as {self.bot.user} ({self.bot.user.id})")
            lines.append(f"Loaded plugins - {self.plugins}")
            lines.append(f"Joined {len(self.bot.guilds)} server(s) - {server_names}")
            lines.append(f"[------------------------STATUS------------------------]")
            return lines

## INITIALIZATION
# This is hacky and bad, but that's this whole bot at this point
# I've learned a lot through making this and would do it quite differently next time
inst = DiscordBot("Extensible bot using Discord.py's Cogs.")

def initialize(instance: DiscordBot) -> commands.Bot:
    """Get the bot, database, and logger ready"""
    # Logger
    log = get_logger(instance.log_file)

    # Discord.py's commands.ext Bot
    bot = commands.Bot(
        commands.when_mentioned_or(instance.config_prefix),
        description=instance.description
    )
    instance.bot = bot

    # Make any required backup and initialize the database
    db_file = f"db/{instance.database}"

    if os.path.exists(db_file) and instance.backup_db:
        timestamp = f"{pretty_datetime(datetime.now(), display='FILE')}"
        try:
            shutil.copyfile(db_file, f"db/backups/{instance.database}-{timestamp}.sql")
        except IOError as e:
            error_file = f"db/backups/{instance.database}-{timestamp}.sql"
            log.error(f"Unable to create file {error_file}\n    - {e}")

    db = SqliteDict(
        filename=f"db/{instance.database}",
        tablename="discord-bot",
        encode=json.dumps,
        decode=json.loads,
        autocommit=True
    )

    if "blacklist" not in db:
        db["blacklist"] = []

    if "servers" not in db:
        db["servers"] = {}

    if "accounts" not in db:
        db["accounts"] = {}

    instance.blacklist = db["blacklist"]
    instance.servers = db["servers"]
    instance.accounts = db["accounts"]

    ## CHECKS
    # Local check for if the user is a botmaster
    def is_botmaster():
        async def predicate(ctx: Context):
            return str(ctx.author.id) in instance.botmasters
        return commands.check(predicate)

    # Global check for if the user is blacklisted
    @bot.check
    def allowed(ctx: Context):
        return str(ctx.author.id) not in instance.blacklist

    # Local check for the user's bot account level
    def level(required=0):
        async def predicate(ctx: Context):
            uid = str(ctx.author.id)
            sid = str(ctx.guild.id)
            # User doesn't have an account
            if sid not in instance.accounts or uid not in instance.accounts[sid]:
                return False
            else:
                return instance.accounts[sid][uid] >= required

        return commands.check(predicate)

    # Global check for if the plugin is enabled on the current server
    @bot.check
    def plugin_enabled(ctx: Context):
        try:
            sid = str(ctx.guild.id)
        # Assume all plugins are available in a direct message
        except AttributeError:
            return True

        # Not a plugin
        if ctx.cog == None:
            return True

        try:
            result = instance.servers[sid][ctx.cog.name]
            return result
        except KeyError:
            # Plugin will default to enabled if not set by a server admin
            return True

    ## EVENTS
    @bot.event
    async def on_ready():
        # If this is the first launch (Not a reconnection from disconnect)
        if instance.first_launch:
            # Load all available plugins
            load_plugins(bot, log, instance.plugins)
            # Set the DiscordBot instance's application info
            instance.app_info = await bot.application_info()

            instance.first_launch = False

        # Print mission control to the console
        log.info("\n".join(instance.mission_control()))

        # Register the servers that the bot has joined
        for server in bot.guilds:
            sid = str(server.id)
            if sid not in instance.servers:
                instance.servers[sid] = {}

        update_db(db, instance.servers, "servers")

    @bot.event
    async def on_guild_join(guild: Guild):
        sid = str(guild.id)

        log.info(f"[JOIN] {guild.name}")

        if sid not in instance.servers:
            instance.servers[sid] = {}
            update_db(db, instance.servers, "servers")

    @bot.event
    async def on_guild_remove(guild: Guild):
        sid = str(guild.id)

        log.info(f"[LEAVE] {guild.name}")

        if sid in instance.servers:
            instance.servers.pop(sid)
            update_db(db, instance.servers, "servers")

    @bot.event
    async def on_message(msg: Message):
        # Log messages to the console/log file if enabled
        if instance.log_messages:
            timestamp = pretty_datetime(datetime.now(), display="TIME")
            message = f"[{msg.guild} - #{msg.channel}] <{msg.author}>: {msg.content}"

            log.info(f"-{timestamp}- {message}")

        # Process the commands from the message afterwards
        await bot.process_commands(msg)

    @bot.event
    async def on_message_edit(former: Message, latter: Message):
        # Embeds cause message edit events even if the user didn't edit them
        if former.content == latter.content and former.embeds != latter.embeds:
            return
        # Log the edit to the console/log file if enabled
        if instance.log_edits:
            timestamp = pretty_datetime(datetime.now(), display="TIME")

            log.info(f"-{timestamp}- [EDIT] [{former.guild}] #{former.channel}")
            log.info(f"[BEFORE] <{former.author}>: {former.content}")
            log.info(f"[AFTER] <{latter.author}>: {latter.content}")

        # Process the commands from the message afterwards if enabled
        if instance.cmd_on_edit:
            await bot.process_commands(latter)

    @bot.event
    async def on_message_delete(msg: Message):
        # Log the delete to the console/log file if enabled
        if instance.log_deletes:
            timestamp = pretty_datetime(datetime.now(), display="TIME")

            header = f"-{timestamp}- [DELETE] "
            content = f"[{msg.guild}] #{msg.channel} <{msg.author}>: {msg.content}"

            log.info(f"{header} {content}")

    @bot.event
    async def on_command(ctx: Context):
        # Log the command to the console/log file if enabled
        if instance.log_commands:
            timestamp = pretty_datetime(datetime.now(), display="TIME")

            command = ctx.message.content
            author = ctx.author

            location = f"[{ctx.guild}] - #{ctx.message.channel}"
            header = f"-{timestamp}- [COMMAND] `{command}`"

            log.info(f"{header} by `{author}` in `{location}`")

    @bot.event
    async def on_command_error(ctx: Context, error):
        # Just send the error to the command's channel
        await ctx.send(f"Error: {error}")

    ## COMMANDS
    # Basic
    @bot.command(name="shutdown")
    @is_botmaster()
    async def cmd_shutdown(ctx: Context):
        """Shut the bot down compeletely."""
        await ctx.send("Shutting down.")
        await bot.logout()

    @bot.command(name="ping")
    async def cmd_ping(ctx: Context):
        """Ping/pong test."""
        await ctx.send(f"Pong {ctx.author.mention}")

    @bot.command(name="info")
    async def cmd_info(ctx: Context):
        """Show the bot's mission control."""
        embed = Embed(title="Status", color=0x7289DA)

        embed.add_field(name="Time", value=pretty_datetime(datetime.now(), "FULL"))
        embed.add_field(name="Version", value=VERSION)

        embed.add_field(
            name="User",
            value=f"{instance.bot.user} ({instance.bot.user.id})",
            inline=False
        )

        embed.add_field(name="Plugins", value=f"[{', '.join(instance.plugins)}]")
        embed.add_field(name="Servers", value=str(len(instance.servers)))

        # Just in case something happened initializing the app info
        if instance.app_info is not None:
            embed.set_author(
                name=instance.app_info.name,
                icon_url=instance.app_info.icon_url
            )

        embed.set_footer(text="https://github.com/Aurexine/DiscordBot")

        await ctx.send(embed=embed)

    @bot.command(name="blacklist", aliases=["bl", "block"])
    @is_botmaster()
    async def cmd_blacklist(ctx: Context, target: User, blacklist = True):
        """Set <Target> (User)'s blacklist status to <Blacklist>."""
        uid = str(target.id)

        if uid in instance.blacklist:
            # Trying to blacklist a user who is already blacklisted
            if blacklist:
                await ctx.send(f"{target.name} is already blacklisted.")
            # Remove a user from the blacklist
            else:
                instance.blacklist.remove(uid)
                await ctx.send(f"{target.name} removed from blacklist.")
        else:
            # Add a user to the blacklist
            if blacklist:
                instance.blacklist.append(uid)
                await ctx.send(f"{target.name} added to blacklist.")
            # Trying to remove a user who is not blacklisted
            else:
                await ctx.send(f"{target.name} is not blacklisted.")

        update_db(db, instance.blacklist, "blacklist")

    # Accounts
    @bot.group(name="account", aliases=["accounts", "accs"])
    @commands.guild_only()
    async def cmd_account(ctx: Context):
        """Add/remove/update accounts.

        Running the command without arguments will display your current account level.
        """
        if ctx.invoked_subcommand is None:
            uid = str(ctx.author.id)
            sid = str(ctx.guild.id)

            if sid not in instance.accounts:
                # Server hasn't been set up
                await ctx.send("Server has no accounts.")
                await ctx.send_help("account genesis")
            elif uid not in instance.accounts[sid]:
                # User has no account
                await ctx.send("You do not have an account for this server.")
            else:
                await ctx.send(f"Your account level is: {instance.accounts[sid][uid]}.")

    @cmd_account.command(name="search", aliases=["lookup", "find"])
    @commands.guild_only()
    async def account_search(ctx: Context, target: Member):
        """Look up <Target> (Member)'s account."""
        uid = str(target.id)
        sid = str(ctx.guild.id)

        if sid in instance.accounts and uid in instance.accounts[sid]:
            await ctx.send(f"{target.name} is level {instance.accounts[sid][uid]}.")
        else:
            await ctx.send("User has no account for this server.")

    @cmd_account.command(name="add", aliases=["create", "new"])
    @commands.guild_only()
    @level(10)
    async def account_add(ctx: Context, target: Member, level: int):
        """Add an account for <Target> (Member) at <Level>."""
        uid = str(target.id)
        sid = str(ctx.guild.id)

        if sid not in instance.accounts:
            # Server hasn't been set up
            await ctx.send("Server has no accounts.")
            return

        if uid not in instance.accounts[sid]:
            instance.accounts[sid][uid] = level

            await ctx.send("Account created.")
            update_db(db, instance.accounts, "accounts")
        else:
            await ctx.send("User already has an account for this server.")

    @cmd_account.command(name="remove", aliases=["delete", "destroy"])
    @commands.guild_only()
    @level(10)
    async def account_remove(ctx: Context, target: Member):
        """Remove <Target> (Member)'s account from the server."""
        uid = str(target.id)
        sid = str(ctx.guild.id)

        if sid not in instance.accounts:
            await ctx.send("Server has no accounts.")
            return
        elif uid not in instance.accounts[sid]:
            await ctx.send("User has no account for this server.")
            return
        else:
            instance.accounts[sid].pop(uid)

            await ctx.send("Account removed.")
            update_db(db, instance.accounts, "accounts")

    @cmd_account.command(name="update", aliases=["change", "modify"])
    @commands.guild_only()
    @level(10)
    async def account_update(ctx: Context, target: Member, level: int):
        """Change <Target> (Member)'s account level to <Level>."""
        uid = str(target.id)
        sid = str(ctx.guild.id)

        if sid not in instance.accounts:
            await ctx.send("Server has no accounts.")
            return
        elif uid not in instance.accounts[sid]:
            await ctx.send("User has no account for this server.")
            return
        else:
            instance.accounts[sid][uid] = level

            update_db(db, instance.accounts, "accounts")
            await ctx.send("Account updated.")

    @cmd_account.command(name="genesis")
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def account_admin(ctx: Context):
        """Set yourself as an administrator of the server to create accounts."""
        uid = str(ctx.author.id)
        sid = str(ctx.guild.id)

        if sid not in instance.accounts:
            instance.accounts[sid] = {}

        if uid not in instance.accounts[sid]:
            instance.accounts[sid][uid] = 10

            await ctx.send("Admin account created.")
            update_db(db, instance.accounts, "accounts")
        else:
            await ctx.send("You already have an account.")

    # Plugins
    @bot.group(name="plugins", aliases=["pl", "cogs"])
    async def cmd_plugins(ctx: Context):
        """Plugin handling.

        Running the command without arguments will list loaded plugins.
        """
        if ctx.invoked_subcommand is None:
            await ctx.send(f"Loaded plugins: {', '.join(instance.plugins)}")

    @cmd_plugins.command(name="load")
    @is_botmaster()
    async def cmd_plugins_load(ctx: Context, name: str):
        """Load plugin (Cog) <Name>. Do not include file extension."""
        if name in instance.plugins:
            await ctx.send(f"Plugin {name}.py already loaded.")
            return

        if not os.path.isfile(f"plugins/{name}.py"):
            await ctx.send(f"Cannot find plugins/{name}.py")
        else:
            try:
                bot.load_extension(f"plugins.{name}")
                instance.plugins.append(name)

                update_db(db, instance.plugins, "plugins")
                await ctx.send(f"Plugin {name}.py successfully loaded.")
            except Exception as e:
                exc = f"{type(e).__name__}, {e}"
                await ctx.send(f"Error loading {name}.py:\n```py\n{exc}\n```")

    @cmd_plugins.command(name="unload")
    @is_botmaster()
    async def cmd_plugins_unload(ctx: Context, name: str):
        """Unload plugin (Cog) <Name>. Do not include file extension."""
        if name not in instance.plugins:
            await ctx.send(f"Plugin {name}.py is not loaded.")
        else:
            try:
                bot.unload_extension(f"plugins.{name}")
                instance.plugins.remove(name)

                update_db(db, instance.plugins, "plugins")
                await ctx.send(f"Plugin {name}.py successfully unloaded.")
            except Exception as e:
                exc = f"{type(e).__name__}, {e}"
                await ctx.send(f"Error unloading {name}.py:\n```py\n{exc}\n```")

    @cmd_plugins.command(name="reload")
    @is_botmaster()
    async def cmd_plugins_reload(ctx: Context, name: str):
        """Reload plugin (Cog) <Name>. Do not include file extension."""
        if name not in instance.plugins:
            await ctx.send(f"Plugin {name}.py is not loaded.")
        else:
            try:
                bot.unload_extension(f"plugins.{name}")
                instance.plugins.remove(name)

                update_db(db, instance.plugins, "plugins")
                await ctx.send(f"Plugin {name}.py successfully unloaded.")

                bot.load_extension(f"plugins.{name}")
                instance.plugins.append(name)

                update_db(db, instance.plugins, "plugins")
                await ctx.send(f"Plugin {name}.py successfully loaded.")
            except Exception as e:
                exc = f"{type(e).__name__}, {e}"
                await ctx.send(f"Error unloading {name}.py:\n```py\n{exc}\n```")


    @cmd_plugins.command(name="enable")
    @level(10)
    async def cmd_plugins_enable(ctx: Context, name: str):
        """Enable a loaded plugin (Cog) <Name> on your server."""
        sid = str(ctx.guild.id)

        if name not in instance.plugins:
            # There is a distinction between server-loaded and bot-loaded plugins
            # therefore I do not include the .py extension here purposefully
            await ctx.send(f"No plugin {name} is loaded.")
            return
        else:
            instance.servers[sid][name] = True

            update_db(db, instance.servers, "servers")
            await ctx.send(f"Plugin {name} enabled on your server.")

    @cmd_plugins.command(name="disable")
    @level(10)
    async def cmd_plugins_disable(ctx: Context, name: str):
        """Disable a loaded plugin (Cog) <Name> on your server."""
        sid = str(ctx.guild.id)

        if name not in instance.plugins:
            await ctx.send(f"No plugin {name} is loaded.")
            return
        else:
            instance.servers[sid][name] = False

            update_db(db, instance.servers, "servers")
            await ctx.send(f"Plugin {name} disabled on your server.")

    # Ensure there is at least one botmaster present before starting the bot
    if instance.botmasters is None:
        raise Exception("No botmasters defined.")

    return bot

# Get user's account level (Not technically a check but needs to be here)
def get_account(server: Guild, member: Member) -> int:
    """Return the account level for a given user.

    Intended for export to Cogs.
    """
    uid = str(member.id)
    sid = str(server.id)

    # Get a temporary instance of the main database
    database = SqliteDict(
        filename=f"db/{inst.database}",
        tablename="discord-bot",
        encode=json.dumps,
        decode=json.loads
    )

    if "accounts" not in database:
        database.close()
        raise KeyError("Database not initialized.")

    db_dict = database["accounts"]
    database.close()

    if sid not in db_dict:
        raise KeyError("Server has no accounts.")

    if uid not in db_dict[sid]:
        raise KeyError("User does not have an account for this server.")
    else:
        return db_dict[sid][uid]

# Exportable version of account level check
def is_level(required=0):
    async def predicate(ctx: Context):
        uid = str(ctx.author.id)
        sid = str(ctx.guild.id)

        db_dict = get_db_dict(f"db/{inst.database}", "discord-bot", "accounts")

        if sid not in db_dict or uid not in db_dict[sid]:
            return False
        else:
            return db_dict[sid][uid] >= required

    return commands.check(predicate)

def main():
    bot = initialize(inst)
    bot.run(inst.config_token)

if __name__ == "__main__":
    main()
