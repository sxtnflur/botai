from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from db.crud import get_localization_text, get_user_language, get_tryon_my_photo
from db.schemas.try_on import TryonPhotoSchema
from bot.keyboards import create_kb_tryon_my_photos
from bot.handlers.try_on.try_on import TryOnStates
from schemas.user import UserData
from services import tryon_service
from bot.utils.messages import send_message, get_message

router = Router()


@router.callback_query(F.data.startswith("try_on_use_my_photos|"))
async def try_on_use_my_photos(call: CallbackQuery, state: FSMContext, user_data: UserData):
    offset = 0
    limit = 10
    try:
        offset = int(call.data.split("|")[1])
        limit = int(call.data.split("|")[2])
    except:
        pass

    data = await state.get_data()
    cloth_category_id: int = data.get("cloth_category_id")
    kb = await create_kb_tryon_my_photos(user_data.id, user_data.language, cloth_category_id,
                                         offset=offset, limit=limit)

    localization_text = await get_localization_text(key="try_on_use_my_photos_message",
                                                    language=user_data.language)
    await send_message(
        message_data={"text": localization_text, "reply_markup": kb,
                      "parse_mode": "html"},
        call=call
    )


@router.callback_query(F.data.startswith("tryon_look_my_photo|"))
async def tryon_look_my_photo(call: CallbackQuery, user_data: UserData):
    kling_task_id = int(call.data.split("|")[1])

    tryon_photo: TryonPhotoSchema = await tryon_service.get_tryon_my_photo(kling_task_id)
    category_name = await get_localization_text(key=tryon_photo.cloth_category.name, language=user_data.language)

    message_data = await get_message(
        message_key="tryon_look_my_photo",
        inline_keyboard=[
            [{"text": "tryon_use_this_model",
              "callback_data": f"tryon_use_this_past_photo|{tryon_photo.id}"}],
            [{"text": "back", "callback_data": "try_on_use_my_photos|0|10"}]
        ],
        inline_keyboard_keys=["tryon_use_this_model", "back"],
        language=user_data.language
    )
    message_data["text"] = message_data.pop("text").format(
        created_at=tryon_photo.created_at.strftime("%H:%M %d.%m.%Y"),
        category=category_name
    )
    try:
        await call.message.delete()
    except:
        pass

    await call.message.answer_photo(
        photo=tryon_photo.human_image,
        **message_data
    )

@router.callback_query(F.data.startswith("tryon_use_this_past_photo|"))
async def tryon_use_this_past_photo(call: CallbackQuery, state: FSMContext, user_data: UserData):
    task_id: int = int(call.data.split("|")[1])
    await state.update_data(human_image_from_past_task_id=task_id)

    message_data = await get_message(
        message_key="tryon_get_cloth_img",
        inline_keyboard=[
            [{"text": "back", "callback_data": "try_on_start"}]
        ],
        inline_keyboard_keys=["back"],
        language=user_data.language
    )
    await send_message(message_data=message_data, call=call)
    await state.set_state(TryOnStates.cloth_photo)