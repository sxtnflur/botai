from datetime import datetime

from pydantic import BaseModel


class UserDataDatabase(BaseModel):
    id: int
    telegram_id: int | None
    language: str | None
    sex: str | None
    is_admin: bool = False
    try_on_last_date: datetime | None
    try_on_remain: int | None

    class Config:
        from_attributes = True