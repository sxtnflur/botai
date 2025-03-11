import asyncio
from .base import FalBase
from .schemas import PayloadFashn
from config import settings


class FalGenImageIdeogram(FalBase[PayloadFashn]):
    url = "fal-ai/ideogram/v2"
    result_schema = PayloadFashn
    base_callback_url = f"{settings.stylist_api_url}/try_on/result/bot/ideogram"

    async def generate(self, prompt: str) -> str:
        return await super(FalGenImageIdeogram, self).generate(
            prompt=prompt
        )

    async def generate_subscribed(self, prompt: str) -> PayloadFashn:
        return await super(FalGenImageIdeogram, self).generate_subscribed(
            prompt=prompt
        )

