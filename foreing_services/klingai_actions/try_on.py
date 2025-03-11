import random
import time
import base64
import aiohttp
import jwt
from foreing_services.klingai_actions.schemas import TaskData


def encode_jwt_token(ak, sk):
    headers = {
        "alg": "HS256",
        "typ": "JWT"
    }
    payload = {
        "iss": ak,
        "exp": int(time.time()) + 1800,
        "nbf": int(time.time())
    }
    token = jwt.encode(payload, sk, headers=headers)
    return token



class KlingTryOn:
    ak: str
    sk: str
    domain = "https://api.klingai.com"

    base_callback_url = "https://no-code.uz/api/try_on/result/bot/kling"

    def __init__(self, ak, sk):
        self.ak = ak
        self.sk = sk

    def _update_headers(self) -> dict:
        api_token = encode_jwt_token(ak=self.ak,
                                     sk=self.sk)
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_token}"
        }

    async def create_task_async(self, human_image: base64,
                     cloth_image: base64,
                      callback_url: str = base_callback_url) -> str | None:
        url = self.domain + "/v1/images/kolors-virtual-try-on"
        data = {
            "model_name": "kolors-virtual-try-on-v1",
            "human_image": human_image,
            "cloth_image": cloth_image,
            "callback_url": callback_url
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                url=url,
                json=data,
                headers=self._update_headers()
            ) as response:
                response.raise_for_status()
                print(f'{response.headers=}')
                print(f'{response.status=}')
                res_json = await response.json(content_type=None)

        print(f'{res_json=}')
        task_id: str = res_json.get("data").get("task_id")
        return task_id

    async def get_task(self, task_id: str) -> TaskData:
        async with aiohttp.ClientSession() as session:
            async with session.get(url=self.domain + "/v1/images/kolors-virtual-try-on/" + task_id,
                                   headers=self._update_headers()) as response:
                res_data = await response.json()
                print(f'{res_data=}')
        return TaskData(**res_data.get("data"))

    async def get_acc_info(self,
                            start_time: int, end_time: int,
                            resource_pack_name: str | None = None) -> dict:

        url = self.domain + "/account/costs"
        params = {
            "start_time": start_time,
            "end_time": end_time
        }
        if resource_pack_name:
            params.update(resource_pack_name=resource_pack_name)

        headers = self._update_headers()
        async with aiohttp.ClientSession() as session:
            async with session.get(url=url, params=params, headers=headers) as response:
                print(f'{response=}')
                result: dict = await response.json(content_type=None)
                print(result)

        return result

