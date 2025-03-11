from datetime import datetime

from aiogram import Router, F
from aiogram.types import Message
from aiogram.utils.deep_linking import create_start_link
import shortuuid
from db.crud import add_admin_bot_link
from foreing_services import Assistant
from schemas.user import UserData
from services import GPTService, VirtualTryOn
from bot.utils.formatting import tg_photo_to_bytes

router = Router()


@router.message(F.text == "/admin_link")
async def get_admin_link(m: Message, user_data: UserData):
    if user_data.is_admin:
        payload = str(shortuuid.random())
        print(payload)
        link = await create_start_link(payload=payload, bot=m.bot, encode=True)
        await add_admin_bot_link(payload=payload)
        await m.answer(str(link))
    else:
        await m.answer("Эта функция доступна только админам")


@router.message(F.text == "/update_assistants_data_from_db")
async def update_assistants_data_from_db(m: Message, user_data: UserData):
    if user_data.is_admin:
        await GPTService().update_assistants_data_from_db()
        await m.answer("Данные обновлены")
    else:
        await m.answer("Эта функция доступна только админам")


@router.message(F.photo & F.caption == "add_to_wardrobe")
async def add_to_wardrobe(m: Message, user_data: UserData):
    photo_bytes: bytes = await tg_photo_to_bytes(file_id=m.photo[-1].file_id, bot=m.bot)
    print(f'{photo_bytes=}')

    # await Assistant().update_assistant_data(
    #     assistant_id="asst_41xKyaFfjQ1ZyoWir1I5KFEP",
    #     tools=[{"type": "file_search"}]
    # )
    await GPTService().add_photo_cloth_to_wardrobe(
        images=[photo_bytes],
        user_id=user_data.id
    )
    await m.answer("Фото добавлено в гардероб")

@router.message(F.text == "/get_files_list")
async def get_files_list(m: Message):
    assistant = Assistant()
    files = await assistant.get_files()
    files = "\n".join([str(f.model_dump()) for f in files])
    await m.answer(files)


@router.message(F.text == "/send_gens_to_users_without_result")
async def send_gens_to_users_without_result(
    m: Message,
    user_data: UserData,
    service = VirtualTryOn()
):
    if user_data.is_admin:
        await m.answer("Начинаю отправку запросов")
        await service.generate_image_for_users_list(
            from_datetime=datetime(
                year=2025, month=1, day=24
            )
        )
        await m.answer("Отправка запросов окончена")
    else:
        await m.answer("У вас недостаточно прав")