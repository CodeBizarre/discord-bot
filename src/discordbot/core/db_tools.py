from typing import Union, List
from sqlitedict import SqliteDict


def update_db(sql_db: SqliteDict, dict_db: Union[dict, List[str]], base_key: str):
    """Update the SQLite DB[key] with the in-memory json copy after changes."""
    try:
        sql_db[base_key] = dict_db
    except Exception as e:
        print(e)
        exit()
