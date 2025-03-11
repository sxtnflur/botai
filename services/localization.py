from typing import List

from caching.redis_caching import default_cached
from db.crud import get_all_texts_by_language, get_all_texts_all_languages
from schemas.localization import TextAllLanguagesSchema
from schemas.user import Language


class LocalizationService:
    @default_cached
    async def get_all_texts_by_language(self, language: Language) -> dict:
        return await get_all_texts_by_language(language=language)

    @default_cached
    async def get_all_texts_all_languages(self) -> TextAllLanguagesSchema:
        return await get_all_texts_all_languages()