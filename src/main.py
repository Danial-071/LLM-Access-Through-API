import os
from fastapi import FastAPI
from dotenv import load_dotenv
from src.routes.changelog import router

load_dotenv()

app = FastAPI()

app.include_router(router)
# Mount the route from changelog.py


@app.get("/")
def root():
    return {"status": "ok"}