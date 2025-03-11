import requests
import time
from config import settings

class Flux:
    api_key: str
    domain: str = "https://api.bfl.ml/v1/"

    def __init__(self, api_key: str = settings.api.BFL):
        self.api_key = api_key

    def _get_headers(self):
        return {
            "accept": "application/json",
            "x-key": self.api_key,
            "Content-Type": "application/json"
        }


    def generate_image(self, prompt: str, width: int, height: int,
                       is_dev: bool = False) -> str:
        if is_dev:
            endpoint = "flux-dev"
        else:
            endpoint = "flux-pro-1.1"

        response = requests.post(self.domain + endpoint,
                                 json={
                                     "prompt": prompt,
                                     "width": width,
                                     "height": height
                                 },
                                 headers=self._get_headers())

        return response.json().get("request_id")

    def get_result(self, request_id: str) -> str | None:
        response = requests.get(url=self.domain + "get_result",
                                params={
                                    "id": request_id
                                },
                                haeders=self._get_headers())
        if response.json().get("status").lower() == "ready":
            return response.json().get("result").get("sample")

    def wait_result(self, request_id: str) -> str:
        while True:
            result_text = self.get_result(request_id)
            if not result_text:
                time.sleep(5)
            else:
                return result_text