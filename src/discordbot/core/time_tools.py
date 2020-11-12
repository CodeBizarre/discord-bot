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

def pretty_timedelta(td: timedelta) -> str:
    """Format timedeltas for messages."""
    # Expand the timedelta's days and seconds to a full scale
    years, rem       = divmod(td.days, 365)
    months, days     = divmod(rem, 30)
    hours, rem       = divmod(td.seconds, 3600)
    minutes, seconds = divmod(rem, 60)

    final = {
        "years": years, "months": months, "days": days,
        "hours": hours, "minutes": minutes, "seconds": seconds
    }

    return "".join(
        [f"{int(value)} {key} " if value > 0 else "" for key, value in final.items()]
    ).rstrip()

def time_parser(span: str, length: int, dt: datetime) -> datetime:
    """Parser to convert length/span combos into a future datetime object"""
    # Pseudo switch/case to return a lambda function for the timedelta
    switcher = {
        "seconds": lambda: timedelta(seconds=length),
        "minutes": lambda: timedelta(minutes=length),
        "hours": lambda: timedelta(hours=length),
        "days": lambda: timedelta(days=length),
        "weeks": lambda: timedelta(weeks=length),
        "months": lambda: timedelta(days=length * 30),
        "years": lambda: timedelta(days=length * 365),
        "max": lambda: timedelta(days=3650)
    }

    if span in switcher:
        case = switcher[span]
    elif span + "s" in switcher:
        case = switcher[span + "s"]
    else:
        raise KeyError("Time parser length/span is not valid.")

    return dt + case()
