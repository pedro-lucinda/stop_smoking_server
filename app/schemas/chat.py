from pydantic import BaseModel
from typing import Optional


class ChatIn(BaseModel):
    message: str


class ThreadOut(BaseModel):
    thread_id: str
