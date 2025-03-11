from typing import List

from db.crud import get_rates, get_rate_, give_user_rate, get_user_rate
from schemas.rate import RateShortSchema, RateSchema
from schemas.user import UserRateData


class RateService:
    async def get_rates(self, user_rate_id: int) -> List[RateShortSchema]:
        return await get_rates(user_rate_id)

    async def get_rate(self, rate_id: int, user_id: int) -> RateSchema:
        return await get_rate_(rate_id=rate_id, user_id=user_id)

    async def give_rate_to_user(self, user_id: int, rate_id: int):
        return await give_user_rate(user_id=user_id, rate_id=rate_id)

    async def get_user_rate(self, user_id: int, translate_by_language: str | None = None) -> UserRateData:
        return await get_user_rate(user_id=user_id, translate_by_language=translate_by_language)