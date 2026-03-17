from fastapi import FastAPI

from services.user_service import get_user

app = FastAPI()


@app.get("/users/{user_id}")
def read_user(user_id: int):
    return get_user(user_id)
