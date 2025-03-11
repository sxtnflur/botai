import asyncio
import datetime
from typing import List

from caching.redis_caching import default_cached
from db.database import connection
from db.sql_models.models import UserGroupRequests, User, Rate, Model, Localization, ModelGroup
from schemas.rate import RateShortSchema, RateSchema
from schemas.user import UserRateData
from sqlalchemy import text, delete, label, select, update, case, insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, load_only, defer, joinedload


@connection
async def get_rate(session, rate_id, language: str, telegram_id: int = None):
    selects = [Rate]

    if telegram_id:
        subquery_user = select(User.rate_id).filter_by(telegram_id=telegram_id).subquery()
        selects.append(label("is_mine", subquery_user == Rate.id))

    stmt = (
        select(*selects).filter_by(id=rate_id)
        .options(
            selectinload(Rate.model_groups).joinedload(ModelGroup.models)
            .joinedload(Model.name).options(
                load_only(getattr(Localization, language)), defer(Localization.key)
            )
        )
    )

    result = await session.execute(stmt)
    return result.one()

@connection
async def get_rate_(session, rate_id, user_id: int = None) -> RateSchema:
    selects = [Rate]

    if user_id:
        subquery_user = select(User.rate_id).filter_by(id=user_id).subquery()
        selects.append(case(
            (subquery_user == Rate.id, True), else_=False
        ).label("is_mine"))
        # selects.append(label("is_mine", subquery_user == Rate.id))

    stmt = (
        select(*selects).filter_by(id=rate_id)
        .options(
            selectinload(Rate.model_groups).joinedload(ModelGroup.models)
        )
    )

    rate, is_mine = (await session.execute(stmt)).one()
    rate.is_mine = is_mine
    return RateSchema.from_orm(rate)


@connection
async def get_my_rate(session: AsyncSession, telegram_id: int, values: list = None):
    stmt = select(Rate)
    if values:
        stmt = stmt.options(load_only(*values))

    stmt = stmt.select_from(Rate).join(User, User.rate_id == Rate.id).filter_by(telegram_id=telegram_id)
    return await session.scalar(stmt)

@connection
async def get_my_rate_values(session: AsyncSession, user_id: int, values: list):
    values = [getattr(Rate, v) for v in values]
    stmt = select(*values).select_from(Rate).join(User, User.rate_id == Rate.id).filter_by(id=user_id)
    return (await session.execute(stmt)).fetchone()


@connection
@default_cached
async def get_rate_prices(session: AsyncSession, rate_id, name_by_language: str = None):
    stmt = (
        select(Rate)
        .options(load_only(Rate.price_stars, Rate.price_uzs))
        .filter_by(id=rate_id)
    )
    if name_by_language:
        stmt = stmt.options(selectinload(Rate.name).options(load_only(getattr(Localization, name_by_language))))
    return await session.scalar(stmt)

@connection
@default_cached
async def get_rate_name(session: AsyncSession, rate_id: int, language: str):
    stmt = (
        select(Rate)
        .options(selectinload(Rate.name).options(load_only(getattr(Localization, language))))
        .filter_by(id=rate_id)
    )
    rate = await session.scalar(stmt)
    return getattr(rate.name, language)

@connection
async def give_user_rate(session: AsyncSession, user_id: int, rate_id: int):
    stmt = update(User).filter_by(id=user_id).values(
        rate_id=rate_id,
        rate_date_end=datetime.datetime.now() + datetime.timedelta(days=30)
    )
    await session.execute(stmt)

    stmt = delete(UserGroupRequests).filter_by(user_id=user_id)
    await session.execute(stmt)

    stmt = """
INSERT INTO users_ai_requests (user_id, group_id, requests)
SELECT :user_id, mg.id, mg.requests_limit
FROM model_groups mg
WHERE mg.rate_id = :rate_id
ON CONFLICT (telegram_id, group_id) DO UPDATE SET
requests = EXCLUDED.requests;
    """
    await session.execute(text(stmt).bindparams(user_id=user_id, rate_id=rate_id))

    await session.commit()


@connection
async def get_user_request_or_token(session: AsyncSession, telegram_id: int, model_id: int, assistant_type: str):

    stmt = """
        UPDATE users u
        SET rate_requests = rate_requests - 1
        FROM rates_ai_models ram, ai_models am
        WHERE u.telegram_id = :telegram_id AND u.rate_date_end > now() AND (
            ram.model_id = :model_id OR (
                am.child_model_id = :model_id AND am.id = ram.model_id AND am.assistant_type = :assistant_type
            )
        )
        RETURNING u.id;
    """
    try:
        result = await session.execute(text(stmt), dict(
            telegram_id=telegram_id, model_id=model_id, assistant_type=assistant_type
        ))
        await session.commit()
    except IntegrityError:
        await session.rollback()
    else:
        user_id = result.scalar()
        print("USERID", user_id)
        if user_id:
            return True

    stmt = """
        UPDATE users_tokens_models utm
        SET tokens = utm.tokens - 1
        FROM users u, ai_models am
        WHERE utm.user_id = u.id AND u.telegram_id = :telegram_id

        AND (
            utm.model_id = :model_id OR (
                am.child_model_id = :model_id AND am.id = utm.model_id AND am.assistant_type = :assistant_type
            )
        )
        RETURNING utm.tokens;
    """

    try:
        await session.execute(text(stmt), dict(
            telegram_id=telegram_id, model_id=model_id, assistant_type=assistant_type
        ))
        await session.commit()
    except IntegrityError as e:
        print("ERROR UTM:", e)
    else:
        return True


@connection
async def give_starter_pack_to_user(session: AsyncSession, user_id: int) -> None:
    stmt = text("""
        INSERT INTO users_ai_requests (user_id, group_id, requests)
        SELECT :user_id, id, requests_limit
        FROM model_groups
        WHERE rate_id IS NULL
        ON CONFLICT DO NOTHING
    """).bindparams(user_id=user_id)

    await session.execute(stmt)
    await session.commit()


# @connection
# async def get_rates(session: AsyncSession, language: str = "ru"):
#     stmt = select(Rate, label("name", getattr(Localization, language))).join(Rate.name)\
#     .options(selectinload(Rate.model_groups).joinedload(ModelGroup.models))
#     print(stmt)
#     result = await session.execute(stmt)
#     print("RESULT:")
#     for r in result.all():
#         r, name = r
#         print(r)
#         print(r.id)
#         print(name)
#         print("MODEL GROUPS:")
#         for model_group in r.model_groups:
#             print(model_group)
#             for model in model_group.models:
#                 print(model)
#
#     print("----")


@connection
async def get_rates(session: AsyncSession, my_rate_id: int) -> List[RateShortSchema]:
    stmt = (
        select(Rate.id, Rate.name_id, label("is_mine", Rate.id == my_rate_id))
        .order_by(Rate.id)
    )
    print(stmt)
    rates = await session.execute(stmt)
    return [RateShortSchema.from_orm(r) for r in rates.fetchall()]


@connection
async def minus_request_user(session: AsyncSession, user_id: int, action: str) -> tuple[str, int] | None:
    stmt = text("""
    UPDATE users_ai_requests
    SET requests = users_ai_requests.requests - 1
    FROM model_group_members mgm, models m
    WHERE
    users_ai_requests.user_id = :user_id
    AND mgm.group_id = users_ai_requests.group_id
    AND m.id = mgm.model_id
    AND m.action = :action
    RETURNING m.model, users_ai_requests.requests
    """).bindparams(
        user_id=user_id, action=action
    )

    try:
        result = await session.execute(stmt)
    except IntegrityError as e:
        print(e)
        await session.rollback()
        return None

    result = result.fetchone()
    if not result:
        await session.rollback()
        return

    model, requests = result

    if requests < 0:
        await session.rollback()
        return

    await session.commit()
    return model, requests


@connection
async def plus_request_user(session: AsyncSession, user_id: int, action: str) -> tuple[str, int] | None:
    stmt = text("""
        UPDATE users_ai_requests
        SET requests = users_ai_requests.requests + 1
        FROM model_group_members mgm, models m
        WHERE
        users_ai_requests.user_id = :user_id
        AND mgm.group_id = users_ai_requests.group_id
        AND m.id = mgm.model_id
        AND m.action = :action
        RETURNING m.model, users_ai_requests.requests
        """).bindparams(
        user_id=user_id, action=action
    )

    try:
        result = await session.execute(stmt)
    except IntegrityError as e:
        print(e)
        await session.rollback()
        return None

    result = result.fetchone()
    if not result:
        await session.rollback()
        return

    model, requests = result

    if requests < 0:
        await session.rollback()
        return

    await session.commit()
    return model, requests


@connection
async def get_user_rate(session: AsyncSession, user_id: int,
                        translate_by_language: str | None = None) -> UserRateData:
    # stmt = (
    #     select(User)
    #     .options(
    #         load_only(
    #             User.rate_id, User.rate_date_end
    #         )
    #     )
    #     .filter(User.id == user_id)
    # )

    options = [
        load_only(User.rate_date_end, User.rate_id)
    ]

    # Добавляем в options подгрузку количества запросов у пользователя и количество моделей на которые эти запросы,
    # а также подгружаем id тарифа каждой группы, чтобы потом понять, привязана ли группа к какому-то тарифу,
    # если не привязана, значит это триальная группа
    option_requests_group = (
        selectinload(User.requests_groups).load_only(UserGroupRequests.requests)
        .options(
            selectinload(UserGroupRequests.group)
            .load_only(ModelGroup.rate_id)
        )
        .joinedload(UserGroupRequests.models)
    )

    # Если нужен перевод, подгружаем перевод названия модели
    if translate_by_language:
        option_requests_group = (
            option_requests_group.joinedload(Model.name)
            .load_only(getattr(Localization, translate_by_language))
        )

    # Добавляем в options подгрузку макс количества токенов на запрос в AI и названия тарифа
    option_user_rate = (
        selectinload(User.rate).load_only(Rate.max_tokens, Rate.name_id)
    )

    # Если нужен перевод, подгружаем перевод названия тарифа
    if translate_by_language:
        option_user_rate = (
            option_user_rate
            .joinedload(Rate.name)
            .load_only(getattr(Localization, translate_by_language))
        )

    options.append(option_requests_group)
    options.append(option_user_rate)

    stmt = select(User).options(*options).filter_by(id=user_id)

    user: User = await session.scalar(stmt)


    user_has_rate = False

    # Если у пользователя закончилось время тарифа, значит тарифа нет
    if user.rate_id and user.rate_date_end and user.rate_date_end < datetime.datetime.now():
        user_has_rate = False
    elif user.rate_id:
        user_has_rate = True

    requests_group = []
    for rg in user.requests_groups:
        """
            Если раскомментить, данные о запросах не будут появляться, если у юзера их нет
        """
        # if (rg.group.rate_id and not user_has_rate) or rg.requests <= 0:
        #     continue
        requests_group.append(rg)

    user.requests_groups = requests_group

    if translate_by_language:
        if user.rate:
            user.rate.name_id = getattr(user.rate.name, translate_by_language)

        for i, rg in enumerate(user.requests_groups):
            for m in rg.models:
                m.name_id = getattr(m.name, translate_by_language)

    if not user_has_rate:
        user.rate_id = None
        user.rate_date_end = None
        user.rate = None

    return UserRateData.from_orm(user)


if __name__ == '__main__':
    asyncio.run(get_user_rate(
        user_id=178
    ))