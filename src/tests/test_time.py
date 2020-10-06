from discordbot.core.time_tools import pretty_datetime, pretty_timedelta, time_parser
from datetime import datetime

sample = datetime.utcfromtimestamp(1501959629)
minus  = datetime.utcfromtimestamp(1501959620)
delta  = sample - minus

def test_pretty_datetime_full():
    dt = pretty_datetime(sample)

    assert dt == "2017-8-5 19:0"

def test_pretty_datetime_time():
    dt = pretty_datetime(sample, "TIME")

    assert dt == "19:0:29"

def test_pretty_datetime_file():
    dt = pretty_datetime(sample, "FILE")

    assert dt == "2017-8-5-19-0"

def test_pretty_timedelta():
    td = pretty_timedelta(delta)

    assert td == "9 seconds"

def test_time_parser():
    case   = time_parser("hours", 1, sample)
    result = pretty_datetime(case)

    assert result == "2017-8-5 20:0"
