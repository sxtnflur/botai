from aiogram import Router, F
from aiogram.types import CallbackQuery
from bot.keyboards import create_kb_choose_language
from bot.messages import settings_message
from schemas.user import UserData
from bot.utils.messages import send_message, get_message

router = Router()


@router.callback_query(F.data == "settings")
async def settings(call: CallbackQuery, user_data: UserData):
    message = await get_message(language=user_data.language, **settings_message)
    await send_message(message_data=message, call=call)


@router.callback_query(F.data == "change_language")
async def change_language(call: CallbackQuery, user_data: UserData):
    kb = await create_kb_choose_language(language=user_data.language, back_callback_data="settings",
                                         is_registration=0)
    message_data: dict = await get_message(message_key="choose_language", language=user_data.language)
    message_data["reply_markup"] = kb
    await send_message(message_data=message_data, call=call)