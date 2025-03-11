import dataclasses
from abc import ABC, abstractmethod
import base64
from typing import List

from fastapi import UploadFile


@dataclasses.dataclass
class Folders:
    PROFILE_PHOTOS = "/users/{user_id}/avatar/"
    SERVICES_PHOTOS = "/services/"
    BOT_KLING_PHOTOS = "/kling/"
    BOT_MODEL_FOR_TRYON = "/kling/models/"
    GPT_GENERATE = "/gpt/gen/"
    GPT_PROMPT = "/gpt/prompt/"


class FileStorage(ABC):
    folders = Folders

    @abstractmethod
    async def upload_file_get_url(self, file: base64, folder: str, filename: str, format: str = "jpg") -> str:
        ...