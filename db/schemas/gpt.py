from datetime import datetime

from pydantic import BaseModel, Field


class ThreadSchema(BaseModel):
    id: int
    thread_id: str
    created_at: datetime
    name: str | None = None
    action_id: int

    class Config:
        from_attributes = True


class AddWardrobeElement(BaseModel):
    image_url: str
    gpt_file_id: str
    name: str
    cloth_category_id: int
