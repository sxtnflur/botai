from foreing_services.flux_service.base import Flux
import aiohttp
import asyncio
from foreing_services.flux_service.schemas import GetResultResponse, Mode, Priority


class FluxAsync(Flux):
    async def __generate_image(self, session: aiohttp.ClientSession,
                               prompt: str, width: int, height: int,
                               image_prompt: str | None = None,
                               mode: Mode = Mode.style,
                               priority: Priority = Priority.quality,
                               is_dev: bool = False) -> str:
        if is_dev:
            endpoint = "flux-dev"
        else:
            endpoint = "flux-pro-1.1"

        async with session.post(self.domain + endpoint,
                                json={
                                    "prompt": prompt,
                                    "width": width,
                                    "height": height,
                                    "mode": mode,
                                    # "image_prompt": image_prompt,
                                    "priority": priority
                                },
                                headers=self._get_headers()) as response:
            res_json = await response.json()
            print(f'{res_json=}')

        request_id: str | None = res_json.get("id")
        if not request_id:
            raise Exception(res_json.get("detail"))
        return request_id


    async def __get_result(self, session: aiohttp.ClientSession, request_id: str) -> GetResultResponse:
        async with session.get(url=self.domain + "get_result",
                                params={
                                    "id": request_id
                                },
                                headers=self._get_headers()) as response:
            res_json = await response.json()
            print(f'{res_json=}')
            return GetResultResponse(**res_json)

    async def generate_image(self, prompt: str, width: int = 1024, height: int = 768,
                             wait_tries: int = 30,
                             is_dev: bool = False) -> GetResultResponse:

        async with aiohttp.ClientSession() as session:
            request_id: str = await self.__generate_image(
                session=session, prompt=prompt,
                width=width, height=height,
                is_dev=is_dev,
                image_prompt="https://i.pinimg.com/originals/8a/cf/64/8acf64e14e3419aac9441aff33e12915.png")

            for i in range(wait_tries):
                result: GetResultResponse = await self.__get_result(session, request_id)
                if result.status == result.status.ready:
                    return result
                else:
                    await asyncio.sleep(5)


    async def get_result(self, request_id: str) -> GetResultResponse:
        async with aiohttp.ClientSession() as session:
            return await self.__get_result(session, request_id)


    async def wait_result(self, request_id: str) -> GetResultResponse:
        async with aiohttp.ClientSession() as session:
            while True:
                result: GetResultResponse = await self.__get_result(session, request_id)
                if result.status == result.status.ready:
                    return result
                else:
                    await asyncio.sleep(5)

    async def send_task_gen_image(self, prompt: str, width: int, height: int,
                               is_dev: bool = False):
        async with aiohttp.ClientSession() as session:
            return await self.__generate_image(
                session, prompt, width, height, is_dev
            )