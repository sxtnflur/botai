import os

import aiohttp
import fal_client
from config import settings
from fal_client import Status, Completed
from foreing_services.fal_service.schemas import Result
from pydantic import BaseModel
from typing_extensions import TypeVar, Generic

ResultT = TypeVar("ResultT", bound=BaseModel)


class FalBase(Generic[ResultT]):
    domain = "https://queue.fal.run/"
    url: str
    base_callback_url: str
    result_schema: ResultT

    """
        Нужно установить ключ в .env
        FAL_KEY="YOUR_API_KEY"
    """

    async def get_status(self, request_id: str):
        return await fal_client.status_async(
            self.url,
            request_id,
            with_logs=True
        )

    async def generate_subscribed(self, **kwargs) -> ResultT:
        result = await fal_client.subscribe_async(
            self.url,
            arguments=kwargs,
            with_logs=True
        )
        print(f'{result=}')
        return self.result_schema.model_validate(result)

    async def generate(self, **kwargs) -> str:
        if not self.base_callback_url:
            raise ValueError("'base_callback_url' не указан")

        handler = await fal_client.submit_async(
            self.url,
            arguments=kwargs,
            webhook_url=self.base_callback_url,
        )
        print(f'{handler=}')
        print(f'{handler.request_id=}')
        print(f'{await handler.status()=}')
        return handler.request_id

    async def get_result(self, request_id: str) -> ResultT | None:
        result = await fal_client.result_async(self.url, request_id)
        if not result:
            return
        return self.result_schema.model_validate(result)

        # status = await self.get_status(request_id)
        # if isinstance(status, Completed):
        #     headers = self.headers
        #     print(f'{headers=}')
        #     async with aiohttp.ClientSession() as session:
        #         async with session.get(url=self.domain + "fal-ai/leffa/requests/" + request_id,
        #                                headers=headers) as response:
        #             result = await response.json()
        #     return self.result_schema.model_validate(result)
        # else:
        #     return None





class FalTryOn(FalBase[ResultT]):
    url = "fal-ai/leffa/virtual-tryon"
    base_callback_url = f"{settings.stylist_api_url}/try_on/result/bot/leffa"
    result_schema = Result

    async def generate(self,
                       human_image: str,
                       cloth_image: str,
                       **kwargs) -> str:

       return await super(FalTryOn, self).generate(
            human_image=human_image,
            cloth_image=cloth_image,
            num_inference_steps=50,
            guidance_scale=2.5,
            enable_safety_checker=True,
            output_format="png"
        )

    async def generate_subscribed(self,
                                  human_image: str,
                                  cloth_image: str,
                                  **kwargs) -> Result:
        return await super(FalTryOn, self).generate_subscribed(
            human_image=human_image,
            cloth_image=cloth_image,
            num_inference_steps=50,
            guidance_scale=2.5,
            enable_safety_checker=True,
            output_format="png"
        )