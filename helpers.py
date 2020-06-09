# Aurexine 2020
# Helper functions to clean out the main file
import sys
import os
import logging
import json

from logging import Logger
from sqlitedict import SqliteDict
from datetime import datetime, timedelta
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

def pretty_timedelta(td: timedelta):
    """Format timedeltas for messages."""
    # Expand the timedelta's days and seconds to a full scale
    years    = td.days // 365
    rem_days = td.days % 365
    months   = rem_days // 30
    rem_days = rem_days % 30
    weeks    = rem_days // 7
    rem_days = rem_days % 7
    days     = rem_days
    hours    = td.seconds // 3600
    rem_secs = td.seconds % 3600
    minutes  = rem_secs // 60
    rem_secs = rem_secs % 60
    seconds  = rem_secs

    final = {
        "year": years,
        "month": months,
        "week": weeks,
        "day": days,
        "hour": hours,
        "minute": minutes,
        "second": seconds
    }

    result = ""

    # Add the scale to the result if it's greater than 0
    for key, value in final.items():
        if value <= 0:
            continue

        if value > 1:
            key += "s"

        result += f"{value} {key} "

    return result

async def time_parser(span: str, length: int, dt: datetime) -> datetime:
    """Parser to convert length/span combos into a future datetime object"""
    # Psuedo switch/case to return a lambda function for the timedelta
    switcher = {
        "seconds": lambda: timedelta(seconds=length),
        "minutes": lambda: timedelta(minutes=length),
        "hours": lambda: timedelta(hours=length),
        "days": lambda: timedelta(days=length),
        "weeks": lambda: timedelta(weeks=length),
        "months": lambda: timedelta(days=length*30),
        "years": lambda: timedelta(days=length*365),
        "max": lambda: timedelta(days=3650)
    }

    if span in switcher:
        # Grab the function from the switcher
        case = switcher[span]
    elif span + "s" in switcher:
        case = switcher[span + "s"]

    # Calculate and return the time in the future
    future = dt + case()
    return future

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

def get_db_dict(file: str, table: str, base_key: str) -> dict:
    """Return a dictionary from an SQLite database without keeping it open."""
    database = SqliteDict(
        filename=file,
        tablename=table,
        encode=json.dumps,
        decode=json.loads
    )

    if base_key not in database:
        database.close()
        raise KeyError("Base key does not exist in database.")
    else:
        db_dict = database[base_key]
        database.close()
        return db_dict

def load_plugins(bot: commands.Bot, logger: Logger, plugins: list):
    """Load available cogs."""
    for p in os.listdir("plugins"):
        p = p.split(".")[0]
        # This wasn't an issue before but is now
        if p == "__pycache__":
            return
        try:
            bot.load_extension(f"plugins.{p}")
            plugins.append(p)
        except Exception as e:
            exc = "{0}: {1}".format(type(e).__name__, e)
            logger.warning(f"Failed to load plugin {p}:\n    - {exc}")
