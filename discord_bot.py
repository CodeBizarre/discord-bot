import os
import shutil
import json

from datetime import datetime
from sqlitedict import SqliteDict
from discord import User
from discord.ext import commands

from helpers import get_logger, pretty_datetime

VERSION = "3.0.0b1"

class DiscordBot(commands.Bot):
    """Extensible bot using Discord.py's Cogs"""
    def _filesystem_setup(self):
        """Ensure all config and database files and folders exist."""
        try:
            # Generate a default config if it doesn't exist
            if not (os.path.exists("config") and os.path.exists("config/config.json")):
                os.makedirs("config")
                with open("config/config.json", "w") as gen:
                    default_config = {
                        "Database": "database.sql",
                        "BackupDB": True,
                        "Botmasters": ["Discord user IDS", "Go here WITH QUOTES"],
                        "Prefix": "~",
                        "MentionCommands": False,
                        "Token": "Bot token goes here",
                        "CommandsOnEdit": True,
                        "DeleteCommands": False,
                        "LogFile": "bot.log",
                        "LogMessages": True,
                        "LogEdits": True,
                        "LogDeletes": True,
                        "LogCommands": True
                    }
                    gen.write(json.dumps(default_config, indent=4))

            if not os.path.exists("db"):
                os.makedirs("db")

            if not os.path.exists("db/backups"):
                os.makedirs("db/backups")

            if not os.path.exists("plugins"):
                os.makedirs("plugins")

        except IOError as e:
            raise IOError(f"Unable to read a config file: {e}") from e
        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(f"Unable to parse json file: {e}")

    def __init__(self, description, *args, **kwargs):
        # Base init
        self.version = VERSION
        self.description = description

        # Discord library
        self.app_info = None

        # Config
        with open("config/config.json") as cfg:
            config = json.load(cfg)
            self.database       = config["Database"]
            self.backup_db      = config["BackupDB"]
            self.config_prefix  = config["Prefix"]
            self.mention_cmds   = config["MentionCommands"]
            self.config_token   = config["Token"]
            self.cmd_on_edit    = config["CommandsOnEdit"]
            self.delete_cmds    = config["DeleteCommands"]
            self.log_file       = config["LogFile"]
            self.log_messages   = config["LogMessages"]
            self.log_edits      = config["LogEdits"]
            self.log_deletes    = config["LogDeletes"]
            self.log_commands   = config["LogCommands"]
            self.botmasters     = config["Botmasters"]

        # Non-config init
        self.log = get_logger(self.log_file)
        self.db = None
        self.blocklist = []
        self.plugins = []
        self.servers = {}
        self.accounts = {}
        self.first_launch = True

        # Database init
        db_file = f"db/{self.database}"

        if os.path.exists(db_file) and self.backup_db:
            timestamp = f"{pretty_datetime(datetime.now(), display='FILE')}"
        try:
            shutil.copyfile(db_file, f"db/backups/{self.database}-{timestamp}.sql")
        except IOError as e:
            error_file = f"db/backups/{self.database}-{timestamp}.sql"
            self.log.error(f"Unable to create file {error_file}\n    - {e}")

        self.db = SqliteDict(
            filename=f"db/{self.database}",
            tablename="discord-bot",
            encode=json.dumps,
            decode=json.loads,
            autocommit=True
        )

        if "blocklist" not in self.db:
            self.db["blocklist"] = []

        if "servers" not in self.db:
            self.db["servers"] = {}

        if "accounts" not in self.db:
            self.db["accounts"] = {}

        self.blocklist = self.db["blocklist"]
        self.servers = self.db["servers"]
        self.accounts = self.db["accounts"]

        super(DiscordBot, self).__init__(
            self.config_prefix, description=description, *args, **kwargs
        )

    # Return current information
    def mission_control(self) -> list:
        if self.guilds is None:
            return ["Bot not initialized."]
        else:
            server_names = [i.name for i in self.guilds]
            return [
                f"[------------------------STATUS------------------------]",
                "Source: https://github.com/Aurexine/discord-bot",
                f"Time: {datetime.now()}",
                f"Version: {self.version}",
                f"Logged in as {self.user} ({self.user.id})",
                f"Loaded plugins - {self.plugins}",
                f"Joined {len(self.guilds)} server(s) - {server_names}",
                f"[------------------------STATUS------------------------]",
            ]
