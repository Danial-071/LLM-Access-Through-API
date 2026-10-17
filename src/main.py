import os
from fastapi import FastAPI
from dotenv import load_dotenv
from src.routes.changelog import router as changelog_router

load_dotenv()

app = FastAPI(title="Changelog API")

# Mount the route from changelog.py
app.include_router(changelog_router)

@app.get("/")
def root():
    return {"status": "ok"}