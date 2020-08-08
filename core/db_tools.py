import json

from sqlitedict import SqliteDict

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
