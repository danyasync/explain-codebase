def query_user(user_id: int):
    with open("users.txt", "r", encoding="utf-8") as handle:
        return {"id": user_id, "name": handle.read().strip()}
