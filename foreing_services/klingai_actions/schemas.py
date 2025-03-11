from datetime import datetime
from typing import List
from pydantic import BaseModel
from enum import Enum


class TaskStatus(str, Enum):
    submitted = "submitted"
    processing = "processing"
    succeed = "succeed"
    failed = "failed"


class TaskImage(BaseModel):
    index: int
    url: str


class TaskResult(BaseModel):
    images: List[TaskImage] | None = None


class TaskData(BaseModel):
    task_id: str
    task_status: TaskStatus
    task_status_msg: str
    created_at: int
    updated_at: int
    task_result: TaskResult


class TryOnClothModelSchema(BaseModel):
    id: int
    model_image: str | None = None
    task_id: str
    created_at: datetime
    is_male: bool
    prompt: str | None = None
    language: str | None = None
    user_telegram_id: int | None = None
    user_id: int | None = None

    class Config:
        from_attributes = True



import datetime
from typing import List

from pydantic import BaseModel


class ImageResult(BaseModel):
    index: int
    url: str


class VideoResult(BaseModel):
    id: str
    url: str
    duration: str


class CallbackProtocol(BaseModel):
    task_id: str
    task_status: str
    task_status_msg: str
    created_at: int
    task_result: TaskResult


class KlingTaskFromDatabase(BaseModel):
    id: int
    task_id: str
    created_at: datetime.datetime
    status: str | None = None
    result_timestamp: datetime.datetime | None = None
    user_id: int | None = None
    user_telegram_id: int | None = None
    language: str

    class Config:
        from_attributes = True


class KlingTaskGet(BaseModel):
    id: int
    task_id: str
    created_at: datetime.datetime
    user_telegram_id: int
    user_id: int
    language: str
    human_image: str | None = None
    human_image_model_id: int | None = None
    cloth_image: str
    cloth_category_id: int

    class Config:
        from_attributes = True