import datetime
from aiogram.types import Message, CallbackQuery
from caching.redis_caching import default_cached
from config import text_timedeltas
from db.database import connection
from bot.keyboards import create_kb_from_texts
from db.sql_models.models import Localization
from sqlalchemy import select, label


async def send_message(message_data: dict, call: CallbackQuery = None, message: Message = None,
                       not_delete: bool = False) -> Message:
    if not message_data.get("parse_mode"):
        message_data["parse_mode"] = "html"

    print(f'{message_data=}')

    if message:
        return await message.answer(**message_data)
    elif call:
        if not_delete:
            try:
                await call.message.delete_reply_markup()
            except:
                pass

            return await call.message.answer(**message_data)
        else:
            try:
                return await call.message.edit_text(**message_data)
            except:
                try:
                    await call.message.delete()
                except:
                    pass

                return await call.message.answer(**message_data)





def get_time_to_datetime(_datetime: datetime.datetime, language: str):
    td = _datetime - datetime.datetime.now()
    if td.days < 0:
        return

    mm, ss = divmod(td.seconds, 60)
    hh, mm = divmod(mm, 60)
    text_timedelta = text_timedeltas.get(language)
    print("DAYS:", td.days)

    return f'{td.days} {text_timedelta.get("d")} {hh} {text_timedelta.get("h")} ' \
           f'{mm} {text_timedelta.get("m")} {ss} {text_timedelta.get("s")}'

@default_cached
@connection
async def get_message(session, message_key: str, language: str,
                      inline_keyboard: list = None, inline_keyboard_keys: list = None,
                      replace_text_params: list = []):
    keys = [message_key]
    if inline_keyboard_keys and inline_keyboard:
        keys += inline_keyboard_keys

    texts = await session.execute(
        select(
            Localization.key, label('text', getattr(Localization, language))
        ).filter(Localization.key.in_(keys))
    )
    texts = {text.key: text.text for text in texts}
    print("TEXTS:", texts)
    message = {}
    message_text = texts.get(message_key)

    for param in replace_text_params:
        replace_to = texts.get(param)
        if replace_to:
            message_text.replace(param, replace_to)


    message["text"] = message_text

    if inline_keyboard_keys and inline_keyboard:
        kb = await create_kb_from_texts(buttons=inline_keyboard, texts=texts)
        message["reply_markup"] = kb

    return message.copy()