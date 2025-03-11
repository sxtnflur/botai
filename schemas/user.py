from datetime import datetime

from pydantic import BaseModel, Field
from enum import Enum



class Language(str, Enum):
    ru = "ru"
    en = "en"
    uz = "uz"

class Gender(str, Enum):
    male = "M"
    female = "F"


class RegistrationStep(str, Enum):
    language = "language"
    sex = "sex"
    done = "done"


class UserMainData(BaseModel):
    id: int
    telegram_id: int | None = None
    is_admin: bool = Field(alias="is_admin_bot")
    firebase_uid: str | None = None
    language: str | None = None
    sex: str | None = None
    try_on_last_date: datetime | None = None
    try_on_remain: int | None = None

    class Config:
        from_attributes = True


class UserData(BaseModel):
    id: int
    telegram_id: int | None
    language: Language | None
    sex: str | None
    registration_step: str | None
    is_admin: bool = False
    try_on_last_date: datetime | None
    try_on_remain: int | None

    class Config:
        from_attributes = True

class UpdateUser(BaseModel):
    language: Language | None = None
    sex: Gender | None = None
    is_admin: bool | None = None


class ShortRate(BaseModel):
    max_tokens: int
    name: str | None = Field(alias="name_id", alias_priority=1)

    class Config:
        from_attributes = True


class ShortModel(BaseModel):
    name: str = Field(alias="name_id")
    class Config:
        from_attributes = True

class RequestGroup(BaseModel):
    requests: int
    models: list[ShortModel]
    class Config:
        from_attributes = True


class UserRateData(BaseModel):
    rate_id: int | None = None
    rate_date_end: datetime | None = None
    rate: ShortRate | None = None
    requests_groups: list[RequestGroup] | None = None

    class Config:
        from_attributes = True


class FirebaseToken(BaseModel):
    uid: str
    token: str
    refresh_token: str

    class Config:
        from_attributes = True