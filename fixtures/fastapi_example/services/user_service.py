from repositories.user_repository import fetch_user


def get_user(user_id: int):
    return fetch_user(user_id)
