from datetime import datetime
from typing import List

from caching.redis_caching import default_cached
from config import MAX_TRY_ON_A_DAY
from db.database import connection
from db.schemas.try_on import ClothCategorySchema, KlingTokenSchema, TryonPhotoSchema
from db.sql_models.models import ClothCategory, KlingTask, Localization, TryonClothModel, User, KlingToken
from foreing_services.klingai_actions.schemas import TryOnClothModelSchema, KlingTaskFromDatabase, KlingTaskGet
from sqlalchemy import select, update, desc, insert, case, or_, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import load_only, selectinload


# Получить категории самого верхнего слоя

@connection
@default_cached
async def get_cloth_categories_first_level(session: AsyncSession) -> List[ClothCategorySchema]:
    stmt = (
        select(ClothCategory)
        .options(
            load_only(ClothCategory.id,
                      ClothCategory.name_id,
                      ClothCategory.garment_type)
        )
        .filter(ClothCategory.parent_id.is_(None))
        .order_by(ClothCategory.ordering)
    )
    cats = await session.scalars(stmt)
    return [ClothCategorySchema.from_orm(cat) for cat in cats]


@connection
@default_cached
async def get_cloth_category(session: AsyncSession, cloth_category_id: int) -> ClothCategorySchema:
    stmt = (
        select(ClothCategory)
        .options(
            load_only(ClothCategory.id, ClothCategory.name_id,
                      ClothCategory.garment_type)
        )
        .filter(ClothCategory.parent_id.is_(None))
        .filter(ClothCategory.id == cloth_category_id)
        .order_by(ClothCategory.ordering)
    )
    cat = await session.scalar(stmt)
    return ClothCategorySchema.from_orm(cat)


# TRYON CLOTH MODELS
@connection
async def minus_try_on_remain(session: AsyncSession, user_id: int) -> bool:
    stmt = (
        update(User)
        .filter(
            and_(User.id == user_id,
                 User.is_admin_bot == True,
                 or_(
                     or_(User.try_on_last_date.is_(None),
                         User.try_on_last_date < func.date(func.now())
                         ),
                     User.try_on_remain > 0
                 ))
        )
        .values(
            try_on_last_date=case(
                (or_(User.try_on_last_date < func.date(func.now()),
                     User.try_on_last_date.is_(None)), func.now()),
                else_=User.try_on_last_date
            ),
            try_on_remain=case(
                (or_(User.try_on_last_date < func.date(func.now()),
                     User.try_on_last_date.is_(None)), MAX_TRY_ON_A_DAY - 1),
                else_=User.try_on_remain - 1
            )
        )
        .returning(User.id)
    )

    user_id: int = await session.scalar(stmt)
    if not user_id:
        return False

    await session.commit()
    return True


@connection
async def add_one_tryon_remain_to_user(session: AsyncSession, user_id: int):
    stmt = (
        update(User).filter(User.id==user_id)
        .values(try_on_remain=User.try_on_remain + 1)
    )
    await session.execute(stmt)
    await session.commit()



@connection
async def add_tryon_cloth_model(
        session: AsyncSession,
        user_id: int, user_telegram_id: int,
        task_id: str, is_male: bool,
        prompt: str | None = None, **kwargs) -> TryOnClothModelSchema:
    stmt = (
        insert(TryonClothModel)
        .values(
            user_id=user_id,
            user_telegram_id=user_telegram_id,
            task_id=task_id,
            is_male=is_male,
            prompt=prompt,
            **kwargs
        )
        .returning(TryonClothModel)
    )
    tryon_cloth_model: TryonClothModel = await session.scalar(stmt)
    await session.commit()
    await session.refresh(tryon_cloth_model)
    return TryOnClothModelSchema.from_orm(tryon_cloth_model)


@connection
async def get_user_tryon_cloth_models(session: AsyncSession,
                                      user_id: int,
                                      offset: int = 0,
                                      limit: int = 10) -> List[TryOnClothModelSchema]:
    stmt = (
        select(TryonClothModel)
        .filter(TryonClothModel.user_id == user_id)
        .order_by(desc(TryonClothModel.id))
        .offset(offset).limit(limit)
    )
    cloth_models = await session.scalars(stmt)
    return [TryOnClothModelSchema.from_orm(model) for model in cloth_models]

@connection
async def get_tryon_cloth_model(session: AsyncSession,
                                model_id: int | None = None,
                                task_id: str | None = None) -> TryOnClothModelSchema | None:
    stmt = select(TryonClothModel)
    if model_id:
        stmt = stmt.filter(TryonClothModel.id == model_id)
    elif task_id:
        stmt = stmt.filter(TryonClothModel.task_id == task_id)
    else:
        return

    result = await session.scalar(stmt)
    if not result:
        return
    return TryOnClothModelSchema.from_orm(result)


@connection
async def update_tryon_cloth_model(session: AsyncSession, task_id: str, **updates) -> TryOnClothModelSchema | None:
    stmt = (
        update(TryonClothModel)
        .values(**updates)
        .filter(TryonClothModel.task_id == task_id)
        .returning(TryonClothModel))
    result = await session.scalar(stmt)
    await session.commit()
    await session.refresh(result)
    if not result:
        return
    return TryOnClothModelSchema.from_orm(result)


@connection
async def get_tryon_my_photos(session: AsyncSession, user_id: int,
                              offset: int = 0, limit: int = 10) -> List[TryonPhotoSchema]:
    stmt = (
        select(KlingTask)
        .options(
            selectinload(
                KlingTask.cloth_category
            ).load_only(ClothCategory.name_id, ClothCategory.id, ClothCategory.garment_type)
        )
        .filter(KlingTask.user_id == user_id)
        .filter(KlingTask.cloth_category_id.is_not(None))
        .filter(KlingTask.human_image.is_not(None))
        .order_by(desc(KlingTask.id))
        .offset(offset).limit(limit)
    )

    res = await session.scalars(stmt)
    return [TryonPhotoSchema.from_orm(r) for r in res]


@connection
async def get_tryon_my_photo(session: AsyncSession, kling_task_id: int) -> TryonPhotoSchema | None:
    stmt = (
        select(KlingTask)
        .options(
            selectinload(
                KlingTask.cloth_category
            ).load_only(ClothCategory.name_id, ClothCategory.garment_type)
        )
        .filter(KlingTask.id == kling_task_id)
    )
    result = await session.scalar(stmt)
    if not result:
        return
    return TryonPhotoSchema.from_orm(result)


@connection
async def update_kling_task(session, task_id: str, **updates):
    stmt = (
        update(KlingTask)
        .where(KlingTask.task_id == task_id)
        .values(**updates)
    )

    await session.execute(stmt)
    await session.commit()

@connection
async def get_kling_tokens(session: AsyncSession) -> List[KlingTokenSchema]:
    kling_tokens = await session.scalars(
        select(KlingToken)
        .filter(
            and_(
                or_(KlingToken.is_expired == False,
                    KlingToken.is_expired.is_(None)),
                or_(KlingToken.remaining_quantity > 0,
                    KlingToken.remaining_quantity.is_(None))
            )
        )
        .order_by(KlingToken.id)
    )
    return [KlingTokenSchema.from_orm(kt) for kt in kling_tokens]

@connection
async def add_kling_task(session: AsyncSession,
                         user_id: int,
                         task_id: str,
                         language: str,
                         cloth_image: str,
                         cloth_category_id: int,
                         human_image: str | None = None,
                         human_image_model_id: int | None = None,
                         human_image_from_past_task_id: int | None = None,
                         user_telegram_id: int | None = None,
                         generated_by_model: str | None = None):
    stmt_insert_task = insert(KlingTask).values(
        user_id=user_id,
        task_id=task_id,
        language=language,
        human_image=human_image,
        human_image_model_id=human_image_model_id,
        cloth_image=cloth_image,
        cloth_category_id=cloth_category_id,
        human_image_from_past_task_id=human_image_from_past_task_id,
        user_telegram_id=user_telegram_id,
        generated_by_model=generated_by_model
    )
    await session.execute(stmt_insert_task)
    await session.commit()

@connection
async def update_values_returning(session, task_id: str, updates: dict) -> KlingTaskFromDatabase:
    stmt = (
        update(KlingTask)
        .where(KlingTask.task_id == task_id)
        .values(**updates)
        .returning(KlingTask)
    )
    task = await session.scalar(stmt)
    await session.commit()
    await session.refresh(task)
    task_data: KlingTaskFromDatabase = KlingTaskFromDatabase.from_orm(task)
    return task_data


@connection
async def get_users_without_result(session, from_datetime: datetime) -> list[KlingTaskGet]:
    stmt = (
        select(KlingTask)
        .filter(KlingTask.result_image.is_(None))
        .filter(KlingTask.created_at >= from_datetime)
        .order_by(KlingTask.id)
    )
    tasks = await session.scalars(stmt)
    return [KlingTaskGet.from_orm(t) for t in tasks]