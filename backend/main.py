import os
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from agent import run_agent

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class CommandRequest(BaseModel):
    text: str


@app.get("/")
def health():
    return {"status": "ok"}


@app.post("/command")
def command(body: CommandRequest):
    try:
        return run_agent(body.text)
    except Exception:
        return {
            "reply": "Something broke, human. Even cats have limits. 🐾",
            "mood": "confused",
            "tools_used": [],
        }
