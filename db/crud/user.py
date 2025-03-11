from datetime import datetime
from typing import Callable, Coroutine, Awaitable

from caching.redis_caching import default_cached
from db.database import connection
from db.sql_models.models import User
from schemas.user import UserMainData, UserData
from sqlalchemy import select, update, text, insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import load_only


@connection
async def get_user_language(session: AsyncSession, telegram_id: int):
    cache_key = default_cached.get_cache_key(f=get_user_language, args=[telegram_id],
                                                   kwargs=dict(telegram_id=telegram_id))
    language = await default_cached.get_from_cache(key=cache_key)
    if language:
        return language

    stmt = select(User).filter_by(telegram_id=telegram_id).options(load_only(User.language))

    user: User | None = (await session.execute(stmt)).scalar_one_or_none()
    if user:
        await default_cached.set_in_cache(key=cache_key, value=user.language)

        return user.language


# @connection
# async def get_user_one_values(session: AsyncSession, telegram_id: int, ):


@connection
async def get_user_registration_data(session: AsyncSession, telegram_id: int):
    stmt = select(User).filter_by(telegram_id=telegram_id).options(load_only(User.language, User.sex,
                                                                             User.is_admin_bot))
    return (await session.execute(stmt)).scalar_one_or_none()


@connection
async def update_user_data(session, telegram_id: int, returning: list[str] = None, **kwargs):
    stmt = update(User).filter(User.telegram_id == telegram_id).values(**kwargs)
    if returning:
        returning = [getattr(User, v) for v in returning]
        stmt = stmt.returning(*returning)
    result = await session.execute(stmt)
    await session.commit()

    if "language" in kwargs and "sex" in kwargs and "is_admin" in kwargs:
        cache_key = default_cached.get_cache_key(f=get_user_registration_data,
                                                       args=[telegram_id],
                                                       kwargs=dict(telegram_id=telegram_id))
        await default_cached.set_in_cache(key=cache_key, value=User(telegram_id=telegram_id, **kwargs))

    if "language" in kwargs:
        cache_key = default_cached.get_cache_key(f=get_user_language,
                                                       args=[telegram_id],
                                                       kwargs=dict(telegram_id=telegram_id))
        await default_cached.set_in_cache(key=cache_key, value=kwargs.get("language"))

    if returning:
        return result.fetchone()

@connection
async def update_user_by_firebase_uid(session, firebase_uid: str, returning: list[str] = None, **kwargs):
    stmt = update(User).filter(User.firebase_uid == firebase_uid).values(**kwargs)
    if returning:
        returning = [getattr(User, v) for v in returning]
        stmt = stmt.returning(*returning)
    result = await session.execute(stmt)
    await session.commit()

    if returning:
        return result.fetchone()


@connection
async def get_user(session, telegram_id: int) -> UserMainData | None:
    stmt = select(User).filter_by(telegram_id=telegram_id)
    stmt = stmt.options(load_only(
        User.id, User.is_admin_bot,
        User.firebase_uid, User.language,
        User.sex, User.try_on_remain, User.try_on_last_date
    ))
    user: User | None = await session.scalar(stmt)
    if not user:
        return

    user.is_admin = user.is_admin_bot
    user.telegram_id = telegram_id
    return UserMainData.from_orm(user)



@connection
async def get_user_values(session, user_id: int, values: list[str]) -> tuple:
    values = [getattr(User, v) for v in values]
    stmt = select(*values).filter_by(id=user_id)
    result = await session.execute(stmt)
    return result.fetchone()


@connection
async def upsert_user(
    session: AsyncSession,
    telegram_id: int,
    first_name: str,
    second_name: str,
    username: str | None,
    is_admin_bot: bool = False,
    try_on_remain: int = 0,
    # post_prepare_object: Callable[[dict], UserData | Coroutine] | None = None
) -> UserMainData:

    text_stmt = """
            insert into users(telegram_id, first_name, second_name, username, is_admin_bot, try_on_remain)
            values(:telegram_id, :first_name, :second_name, :username, :is_admin_bot, :try_on_remain)
            on conflict (telegram_id) do update set
            first_name = excluded.first_name,
            second_name = excluded.second_name,
            username = excluded.username,
            is_admin_bot = (CASE WHEN users.is_admin_bot is true THEN true ELSE excluded.is_admin_bot END),
            try_on_remain = (CASE WHEN users.try_on_remain IS NULL OR users.try_on_remain > excluded.try_on_remain
                                THEN users.try_on_remain
                                ELSE excluded.try_on_remain END)
            RETURNING id, language, sex, is_admin_bot, try_on_remain, try_on_last_date
        """

    res = await session.execute(statement=text(text_stmt).bindparams(
        telegram_id=telegram_id, first_name=first_name,
        second_name=second_name, username=username,
        is_admin_bot=is_admin_bot, try_on_remain=try_on_remain
    ))
    user_id, language, sex, is_admin_bot, try_on_remain, try_on_last_date = res.first()
    user_dict = {"id": user_id, "language": language, "sex": sex,
                 "is_admin_bot": is_admin_bot, "try_on_remain": try_on_remain,
                 "try_on_last_date": try_on_last_date,
                 "telegram_id": telegram_id}
    await session.commit()

    # if post_prepare_object:
    #     user_data: UserData | Coroutine = post_prepare_object(user_dict)
    #     if isinstance(user_data, Coroutine):
    #         return await user_data

    return UserMainData(**user_dict)


@connection
async def insert_user_by_firebase(session: AsyncSession, firebase_uid: str,
                                   **data) -> int:
    stmt = (
        insert(User)
        .values(firebase_uid=firebase_uid,
                **data)
        .returning(User.id)
    )
    user_id: int = await session.scalar(stmt)
    await session.commit()
    return user_id


@connection
async def get_user_by_firebase_uid(session: AsyncSession, firebase_uid: str) -> UserMainData:
    print(f'{firebase_uid=}')
    stmt = select(User).filter_by(firebase_uid=firebase_uid).options(load_only(User.language, User.id,
                                                                               User.firebase_uid,
                                                                               User.telegram_id,
                                                                             User.is_admin_bot,
                                                                               User.sex,
                                                                               User.try_on_remain,
                                                                               User.try_on_last_date))
    res = await session.scalar(stmt)
    print(f'{res=}')
    return UserMainData.from_orm(res)