from typing import List

from caching.redis_caching import default_cached
from db.database import connection
from db.sql_models.models import Localization
from schemas.localization import TextAllLanguagesSchema
from sqlalchemy import select, label
from sqlalchemy.ext.asyncio import AsyncSession



@connection
@default_cached
async def get_localization_text(session: AsyncSession, key: str, language: str):
    res = await session.execute(
        select(
            label('text', getattr(Localization, language))
        ).filter(Localization.key == key)
    )
    return res.scalar()



@connection
@default_cached
async def get_localization_texts(session: AsyncSession, keys: list[str], language: str):
    res = await session.execute(
        select(
           Localization.key, label('text', getattr(Localization, language))
        ).filter(Localization.key.in_(keys))
    )
    res = {key: text for key, text in res}
    return res


@connection
@default_cached
async def get_all_texts_by_language(session: AsyncSession, language: str) -> dict:
    stmt = (
        select(Localization.key, label('text', getattr(Localization, language)))
    )
    texts = await session.execute(stmt)
    return {k: v for k, v in texts}


@connection
@default_cached
async def get_all_texts_all_languages(session: AsyncSession) -> TextAllLanguagesSchema:
    stmt = (
        select(Localization)
    )
    texts = await session.scalars(stmt)
    ru = {}
    en = {}
    uz = {}
    for t in texts:
        ru[t.key] = t.ru
        en[t.key] = t.en
        uz[t.key] = t.uz

    return TextAllLanguagesSchema(ru=ru, en=en, uz=uz)