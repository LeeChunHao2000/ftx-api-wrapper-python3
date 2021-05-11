from time import time as _time


def get_current_timestamp():
    return int(round(_time() * 1_000))


def build_query(**kwargs):
    query = {}
    for key, value in kwargs.items():
        if value is not None:
            query[key] = value
    return query
