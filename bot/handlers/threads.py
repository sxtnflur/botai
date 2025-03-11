from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from db.crud import get_localization_text
from db.schemas.gpt import ThreadSchema
from foreing_services.gpt_actions.assistant import Assistant
from bot.keyboards import create_kb_threads, get_kb_gpt
from schemas.user import UserData
from services import gpt_service

router = Router()

@router.callback_query(F.data.startswith("threads|"))
async def thread(call: CallbackQuery, user_data: UserData):
    offset = 0
    limit = 10
    action_id = 1
    try:
        action_id = int(call.data.split("|")[1])
        offset = int(call.data.split("|")[2])
        limit = int(call.data.split("|")[3])
    except:
        pass

    text = await get_localization_text(key="dialogues_msg", language=user_data.language)
    reply_markup = await create_kb_threads(
        user_id=user_data.id,
        language=user_data.language,
        action_id=action_id, offset=offset, limit=limit
    )
    await call.message.edit_text(
        text=text, reply_markup=reply_markup, parse_mode="html"
    )


@router.callback_query(F.data.startswith("get_thread|"))
async def get_thread_handler(call: CallbackQuery, state: FSMContext, user_data: UserData):
    thread_id = int(call.data.split("|")[1])
    thread: ThreadSchema | None = await gpt_service.get_user_gpt_thread(user_id=user_data.id, thread_id=thread_id)
    # thread = await get_thread(telegram_id=call.from_user.id, thread_id=thread_id)

    reply_markup = await get_kb_gpt(language=user_data.language, action_id=thread.action_id,
                                    btn_back_data=f"threads|{thread.action_id}|0|10")

    assistant = Assistant()
    last_message_text = await assistant.get_last_message(thread_id=thread.thread_id)
    print(f"{last_message_text=}")

    await state.update_data(
        action_id=thread.action_id, thread_id=thread.thread_id
    )
    await call.message.edit_text(
        text=last_message_text, reply_markup=reply_markup, parse_mode="Markdown"
    )
