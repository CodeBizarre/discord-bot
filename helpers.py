import sys
import os
import logging
import json

from logging import Logger
from sqlitedict import SqliteDict
from datetime import datetime, timedelta

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
    years, rem       = divmod(td.days, 365)
    months, days     = divmod(rem, 30)
    hours, rem       = divmod(td.seconds, 3600)
    minutes, seconds = divmod(rem, 60)

    final = {
        "years": years, "months": months,"days": days,
        "hours": hours, "minutes": minutes, "seconds": seconds
    }

    return "".join(
        [f"{int(value)} {key} " if value > 0 else "" for key, value in final.items()]
    ).rstrip()

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
        case = switcher[span]
    elif span + "s" in switcher:
        case = switcher[span + "s"]
    else:
        raise KeyError("Time parser length/span is not valid.")

    return dt + case()

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

def update_db(sql_db: SqliteDict, dict_db: dict, base_key: str):
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
