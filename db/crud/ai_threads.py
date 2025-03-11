from typing import List

from db.database import connection
from db.schemas.gpt import ThreadSchema
from db.sql_models.models import Thread, User
from sqlalchemy import update, select, desc, insert
from sqlalchemy.ext.asyncio import AsyncSession


@connection
async def create_new_thread(session: AsyncSession, thread_id: str, user_id: int,
                            action_id: int = None) -> int:
    stmt = insert(Thread).values(thread_id=thread_id, user_id=user_id, action_id=action_id).returning(Thread.id)
    db_thread_id: int = await session.scalar(stmt)
    await session.commit()
    return db_thread_id

# @connection
# async def create_new_thread(session: AsyncSession, thread_id: str, user_id: int,
#                             action_id: int = None):
#     stmt = update(User).values(thread_id=thread_id).where(User.id == user_id)
#     await session.execute(stmt)
#     await session.commit()


@connection
async def update_thread(session: AsyncSession, thread_id: str, user_id: int, **kwargs):
    stmt = update(Thread).filter_by(thread_id=thread_id, user_id=user_id).values(**kwargs)
    await session.execute(stmt)
    await session.commit()

@connection
async def get_thread(session: AsyncSession, user_id: int, thread_id: int) -> ThreadSchema | None:
    stmt = select(Thread).filter_by(user_id=user_id, id=thread_id)
    result = await session.scalar(stmt)
    if not result:
        return None
    return ThreadSchema.from_orm(result)


@connection
async def get_user_threads(session: AsyncSession, user_id: int,
                           action_id: int | None = None,
                           offset: int = 0, limit: int = 10) -> List[ThreadSchema]:
    stmt = select(Thread).filter_by(user_id=user_id)
    if action_id:
        stmt = stmt.filter_by(action_id=action_id)

    stmt = stmt.offset(offset).limit(limit).order_by(desc(Thread.id))
    threads = await session.scalars(stmt)
    return [ThreadSchema.from_orm(t) for t in threads]