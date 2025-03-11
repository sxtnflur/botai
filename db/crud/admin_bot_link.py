from db.database import connection
from db.sql_models.models import AdminBotLink
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession


@connection
async def add_admin_bot_link(session: AsyncSession, payload: str):
    session.add(AdminBotLink(payload=payload))
    await session.commit()


@connection
async def check_admin_bot_payload(session: AsyncSession, payload: str) -> bool:
    stmt = delete(AdminBotLink).filter(AdminBotLink.payload == payload).returning(AdminBotLink.payload)

    is_deleted = await session.scalar(stmt)
    if is_deleted:
        await session.commit()
        return True
    return False