from typing import List

from db.database import connection
from db.schemas.gpt import AddWardrobeElement
from db.sql_models.models import Model, GptAssistant, User, WardrobeElement
from schemas.gpt import GPTAssistantSchema, WardrobeElementResponse, WardrobeElementDeleted
from sqlalchemy import text, update, select, desc, and_, insert, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import load_only


@connection
async def get_available_ai_models_geneterator(session, telegram_id):

    stmt = """
        SELECT ((utm.tokens > 0) OR
        (rates_ai_models.model_id = ai_models.id AND
        users.rate_date_end > now() AND users.rate_requests > 0)) AS is_available,
        ai_models.model_id,
        ai_models.assistant_type
        FROM ai_models
        JOIN users ON users.telegram_id = :telegram_id
        LEFT JOIN users_tokens_models utm ON utm.model_id = ai_models.id AND utm.user_id = users.id
        LEFT JOIN rates ON rates.id = users.rate_id
        LEFT JOIN rates_ai_models ON rates_ai_models.rate_id = rates.id
        WHERE ai_models.assistant_type != 'all'
    """

    return await session.execute(text(stmt), dict(telegram_id=telegram_id))



async def create_buttons_assistants(telegram_id: int):
    assistants_buttons = []
    assistant_types = {}

    for r in await get_available_ai_models_geneterator(telegram_id):

        print(r)
        is_available, model_id, assistant_type = r
        if assistant_types.get(assistant_type):
            continue

        assistant_types[assistant_type] = is_available


    for assistant_type, is_available in assistant_types.items():
        btn = {"text": assistant_type,
               "callback_data": f"chooseAssistant|{assistant_type}"}
        if not is_available:
            btn["end_emoji"] = "❌"
            btn["callback_data"] = "chooseAssistant|blocked"
        assistants_buttons.append(btn)

    # assistant_types["btn_rates"] = True
    return [assistants_buttons, [{"text": "btn_rates", "callback_data": "rates|no"}]], \
           list(assistant_types.keys()) + ["btn_rates"]


@connection
async def get_model_by_action(session: AsyncSession, action: str, user_id: int) -> tuple[int, str] | None:
    stmt = text(
        """
        SELECT m.id, m.model
        FROM users_ai_requests ur
        JOIN model_group_members mgm ON mgm.group_id = ur.group_id
        JOIN models m ON m.id = mgm.model_id AND m.action = :action
        WHERE ur.user_id = :user_id
        """
    ).bindparams(
        action=action, user_id=user_id
    )
    model = await session.execute(stmt)
    if not model:
        return None
    model_id, model_action = model.first()
    return model_id, model_action


@connection
async def update_model_data(session: AsyncSession, model: str, action: str, **updates):
    stmt = (
        update(Model)
        .filter(Model.model == model)
        .filter(Model.action == action)
        .values(**updates)
    )
    await session.execute(stmt)
    await session.commit()


@connection
async def get_all_assistants(session: AsyncSession) -> List[GPTAssistantSchema]:
    stmt = (
        select(GptAssistant)
        .order_by(desc(GptAssistant.id))
    )
    result = await session.scalars(stmt)
    return [GPTAssistantSchema.from_orm(r) for r in result]


@connection
async def get_assistant(session: AsyncSession, id: int) -> GPTAssistantSchema:
    stmt = (
        select(GptAssistant)
        .filter(GptAssistant.id == id)
    )
    result = await session.scalar(stmt)
    return GPTAssistantSchema.from_orm(result)

@connection
async def get_user_thread_id(session: AsyncSession, user_id: int) -> str | None:
    stmt = (
        select(User.thread_id)
        .where(User.id == user_id)
    )
    return await session.scalar(stmt)


@connection
async def add_wardrobe_elements(session: AsyncSession,
                                wardrobe_elements: List[AddWardrobeElement], user_id: int) -> None:
    wardrobe_elements = [WardrobeElement(
        user_id=user_id, image_url=we.image_url,
        gpt_file_id=we.gpt_file_id,
        name=we.name,
        cloth_category_id=we.cloth_category_id
    ) for we in wardrobe_elements]
    session.add_all(wardrobe_elements)
    await session.commit()

@connection
async def add_wardrobe_element(session: AsyncSession,
                                wardrobe_element: AddWardrobeElement, user_id: int) -> int:
    stmt = insert(WardrobeElement).values(
        user_id=user_id, image_url=wardrobe_element.image_url,
        gpt_file_id=wardrobe_element.gpt_file_id,
        name=wardrobe_element.name,
        cloth_category_id=wardrobe_element.cloth_category_id
    ).returning(WardrobeElement.id)
    we_id: int = await session.scalar(stmt)
    await session.commit()
    return we_id


@connection
async def delete_wardrobe_element(session: AsyncSession, wardrobe_element_id: int,
                                  user_id: int) -> WardrobeElementDeleted | None:
    stmt = delete(WardrobeElement).filter(
        and_(WardrobeElement.id == wardrobe_element_id,
             WardrobeElement.user_id == user_id)
    ).returning(WardrobeElement.gpt_file_id)
    gpt_file_id = (await session.execute(stmt)).first()
    if not gpt_file_id:
        return

    await session.commit()
    return WardrobeElementDeleted(
        gpt_file_id=gpt_file_id
    )

@connection
async def get_user_wardrobe_elements(session: AsyncSession,
                                     user_id: int,
                                     cloth_category_id: int = None,
                                     offset: int = 0, limit: int | None = None) -> List[WardrobeElementResponse]:
    stmt = (
        select(WardrobeElement)
        .filter(WardrobeElement.user_id == user_id)
        .order_by(WardrobeElement.id.desc())
        .offset(offset)
    )

    if cloth_category_id:
        stmt = stmt.filter(WardrobeElement.cloth_category_id == cloth_category_id)

    if limit:
        stmt = stmt.limit(limit)

    wardrobe_elements = await session.scalars(stmt)
    return [WardrobeElementResponse.from_orm(we) for we in wardrobe_elements]

@connection
async def get_user_wardrobe_element(session: AsyncSession,
                                     user_id: int,
                                    wardrobe_element_id: int) -> WardrobeElementResponse | None:
    stmt = select(WardrobeElement).filter(and_(WardrobeElement.user_id == user_id,
                                               WardrobeElement.id == wardrobe_element_id))
    we = await session.scalar(stmt)
    if not we:
        return
    return WardrobeElementResponse.from_orm(we)
