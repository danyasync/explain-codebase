from db.client import query_user


def fetch_user(user_id: int):
    return query_user(user_id)
