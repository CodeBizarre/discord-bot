# Aurexine 2020
# Helper functions to clean out the main file
import sys
import os
import logging
import json

from logging import Logger
from sqlitedict import SqliteDict
from datetime import datetime
from discord.ext import commands

def pretty_datetime(dt: datetime, display: str = "FULL") -> str:
    """Format date/timestamps for messages."""
    if display.upper() == "FULL":
        return f"{dt.year}-{dt.month}-{dt.day} {dt.hour}:{dt.minute}"
    elif display.upper() == "TIME":
        return f"{dt.hour}:{dt.minute}:{dt.second}"
    elif display.upper() == "FILE":
        return f"{dt.year}-{dt.month}-{dt.day}-{dt.hour}-{dt.minute}"
    else:
        return f"Unknown/incorrect display argument for pretty_datetime(): {display}"

def get_logger(file_name) -> Logger:
    """Get an instance of Logger and set up log files."""
    timestamp = pretty_datetime(datetime.now(), "FILE")
    log_file = f"logs/{timestamp}_{file_name}"

    if not os.path.exists("logs"):
        try:
            os.makedirs("logs")
        except IOError as e:
            print(e)
            exit()

    log = logging.getLogger()
    log.setLevel(logging.INFO)
    log.addHandler(logging.FileHandler(filename=log_file, encoding="utf-8"))
    log.addHandler(logging.StreamHandler(sys.stdout))
    return log

def update_json(db: str, name: str):
    """Update a JSON config file to match the in-memory copy after changes."""
    try:
        with open(f"db/{name}.json", "w") as dbfile:
            json.dump(db, dbfile, indent=4)
    except IOError as e:
        print(e)
        exit()

# Fun fact this saves like 2 characters per use
def update_db(sql_db: SqliteDict, dict_db: str, base_key: str):
    """Update the SQLite DB[key] with the in-memory json copy after changes."""
    try:
        sql_db[base_key] = dict_db
    except Exception as e:
        print(e)
        exit()

def load_plugins(bot: commands.Bot, logger: Logger, plugins: list):
    """Load available cogs."""
    for p in os.listdir("plugins"):
        p = p.rstrip(".py")
        # This wasn't an issue before but is now
        if p == "__pycache__":
            return
        try:
            bot.load_extension(f"plugins.{p}")
            plugins.append(p)
        except Exception as e:
            exc = "{0}: {1}".format(type(e).__name__, e)
            logger.warning(f"Failed to load plugin {p}:\n    - {exc}")
