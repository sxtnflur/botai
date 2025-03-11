from enum import Enum
from pydantic import BaseModel


class VtGarmentType(str, Enum):
    upper_body = "upper_body"
    lower_body = "lower_body"
    dresses = "dresses"


class ResultImage(BaseModel):
    path: str | None = None
    url: str
    orig_name: str | None = None