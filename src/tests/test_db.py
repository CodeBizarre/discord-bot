import json

from discordbot.core.db_tools import update_db

from sqlitedict import SqliteDict

def test_update_db():
    db = SqliteDict(
        tablename="test",
        encode=json.dumps,
        decode=json.loads,
        autocommit=True
    )
    val = "01189998819991197253"

    dict_db = db["test"] = {}
    dict_db["value"] = val

    update_db(db, dict_db, "test")

    assert db["test"]["value"] == val
    db.close()
