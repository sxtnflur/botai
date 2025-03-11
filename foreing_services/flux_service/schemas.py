from pydantic import BaseModel
from enum import Enum

class Status(str, Enum):
    task_not_found = "Task not found"
    pending = "Pending"
    request_moderated = "Request Moderated"
    content_moderated = "Content Moderated"
    ready = "Ready"
    error = "Error"


class Result(BaseModel):
    sample: str


class GetResultResponse(BaseModel):
    id: str
    status: Status
    result: Result | None


class Mode(str, Enum):
    character = "character"
    product = "product"
    style = "style"
    general = "general"


class Priority(str, Enum):
    speed = "speed"
    quality = "quality"