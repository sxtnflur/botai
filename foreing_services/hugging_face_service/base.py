import random
from abc import abstractmethod
from typing import Any, Type

import requests
from foreing_services.hugging_face_service.schemas import GeneralGarmentType
from gradio_client import Client, handle_file
from config import settings
from gradio_client.client import Job


class HF:
    src: str = ...

    def __init__(self, hf_token: str | None = settings.api.HUGGING_FACE,
                 duplicate_to_id: str | None = None):
        if duplicate_to_id:
            self.client = Client.duplicate(self.src, hf_token=hf_token, to_id=duplicate_to_id)
        else:
            self.client = Client(self.src, hf_token=hf_token, download_files=False)

    def _predict(self, **kwargs) -> Any:
        return self.client.predict(
            **kwargs
        )

    def get_private_image_url(self, image_url: str) -> bytes:
        return requests.get(
            url=image_url,
            headers={
                "Authorization": f"Bearer {settings.api.HUGGING_FACE}"
            }
        ).content

    def get_result(self, job: Job) -> str:
        result = job.result()
        print(f'{result=}')
        return result[0].get("url")

    def get_result_as_bytes(self, job: Job) -> bytes:
        result = job.result()
        return self.get_private_image_url(image_url=result[0].get("url"))

    @abstractmethod
    def generate_image(self,
                       human_image_url: str,
                       cloth_image_url: str,
                       garment_type: GeneralGarmentType) -> str:
        ...