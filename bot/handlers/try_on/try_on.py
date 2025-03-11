from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import CallbackQuery, Message
from db.crud import add_one_tryon_remain_to_user, get_localization_text
from db.schemas.try_on import GenerateTryOnResponse, GenerateTryOnStatus
from foreing_services.klingai_actions.schemas import TaskData, TaskStatus
from bot.utils.formatting import tg_image_to_b64
from bot.messages import get_message_tryon_select_cloth_cats
from schemas.gpt import GPTResponseStatus
from schemas.user import UserData
from services import tryon_service
from bot.utils.messages import get_message, send_message

router = Router()


class TryOnStates(StatesGroup):
    human_photo = State()
    cloth_photo = State()
    generate_model_prompt = State()


@router.callback_query(F.data == "try_on_start")
async def try_on_start(call: CallbackQuery, user_data: UserData):
    message_data = await get_message_tryon_select_cloth_cats(language=user_data.language)
    try:
        await call.message.delete()
    except:
        pass
    message_data["caption"] = message_data.pop("text")
    await call.message.answer_photo(
        **message_data,
        photo="https://imgintop-stylist.b-cdn.net/bot/41ca52d5-3b40-45c3-a7ed-5013c45cfec7.jpg",
        parse_mode="html",
    )


@router.callback_query(F.data.startswith("try_on_select_cat|"))
async def try_on_select_cat(call: CallbackQuery, state: FSMContext, user_data: UserData):
    cloth_category_id = int(call.data.split("|")[1])
    await state.update_data(cloth_category_id=cloth_category_id)

    message_data = await get_message(
        message_key="tryon_get_human_img",
        inline_keyboard=[
            [{"text": "try_on_use_my_photos", "callback_data": "try_on_use_my_photos|0|10"}],
            [{"text": "try_on_use_model", "callback_data": "try_on_use_model"}],
            [{"text": "back", "callback_data": "try_on_start"}]
        ],
        inline_keyboard_keys=["back", "try_on_use_model", "try_on_use_my_photos"],
        language=user_data.language
    )
    await send_message(message_data=message_data, call=call)
    await state.set_state(TryOnStates.human_photo)


@router.message(TryOnStates.human_photo, F.photo)
async def get_human_photo(m: Message, state: FSMContext, user_data: UserData):
    await state.update_data(human_photo=m.photo[-1].file_id)

    message_data = await get_message(
        message_key="tryon_get_cloth_img",
        inline_keyboard=[
            [{"text": "back", "callback_data": "try_on_start"}]
        ],
        inline_keyboard_keys=["back"],
        language=user_data.language
    )
    await send_message(message_data=message_data, message=m)
    await state.set_state(TryOnStates.cloth_photo)


@router.message(TryOnStates.cloth_photo, F.photo)
async def get_cloth_photo(m: Message, state: FSMContext, user_data: UserData):
    data = await state.get_data()
    human_photo_file_id: str | None = data.get("human_photo")
    human_image_model_id: int | None = data.get("human_image_model_id")
    human_image_from_past_task_id: int | None = data.get("human_image_from_past_task_id")

    cloth_photo_file_id = m.photo[-1].file_id

    cloth_category_id = data.get("cloth_category_id")

    await state.clear()

    # CONVERT TO BASE64
    cloth_photo_b64 = await tg_image_to_b64(file_id=cloth_photo_file_id, bot=m.bot)

    if human_photo_file_id:
        human_photo_b64 = await tg_image_to_b64(file_id=human_photo_file_id, bot=m.bot)

        response: GenerateTryOnResponse = await tryon_service.generate_image(
            user_id=user_data.id,
            language=user_data.language,
            cloth_category_id=cloth_category_id,
            human_image=human_photo_b64,
            cloth_image=cloth_photo_b64,
            user_telegram_id=m.from_user.id,
            is_admin=user_data.is_admin
        )
    elif human_image_model_id:
        response: GenerateTryOnResponse = await tryon_service.generate_image_by_human_image_model_id(
            user_id=user_data.id,
            language=user_data.language,
            cloth_category_id=cloth_category_id,
            human_image_model_id=human_image_model_id,
            cloth_image_b64=cloth_photo_b64,
            user_telegram_id=m.from_user.id,
            is_admin=user_data.is_admin
        )
    elif human_image_from_past_task_id:
        response: GenerateTryOnResponse = await tryon_service.generate_image_by_human_image_past_photo(
            user_id=user_data.id,
            language=user_data.language,
            cloth_category_id=cloth_category_id,
            kling_task_id=human_image_from_past_task_id,
            cloth_image_b64=cloth_photo_b64,
            user_telegram_id=m.from_user.id,
            is_admin=user_data.is_admin
        )
    else:
        return

    print(f'{response=}')

    if response.status == GenerateTryOnStatus.client_has_not_requests:
        message_data = await get_message(
            message_key="cant_use_model_anymore",
            language=user_data.language,
            inline_keyboard=[
                [{"text": "back", "callback_data": "change_assistant"}]
            ],
            inline_keyboard_keys=["back"]
        )
        await send_message(message_data, message=m)
        return

    elif response.status == GenerateTryOnStatus.server_has_not_requests:
        message_data = await get_message(
            message_key="ai_model_doesnot_work",
            language=user_data.language,
            inline_keyboard=[
                [{"text": "back", "callback_data": "change_assistant"}]
            ],
            inline_keyboard_keys=["back"]
        )
        await send_message(message_data, message=m)
        return

    message_data = await get_message(
        message_key="tryon_wait_message",
        language=user_data.language,
        inline_keyboard=[
            # [{"text": "tryon_get_task_status", "callback_data": f"tryon_get_task_status|{response.task_id}"}],
            [{"text": "back", "callback_data": "change_assistant"}]
        ],
        inline_keyboard_keys=["back", "tryon_get_task_status"]
    )
    await send_message(message_data, message=m)


@router.callback_query(F.data.startswith("tryon_get_task_status|"))
async def tryon_get_task_status(call: CallbackQuery, state: FSMContext, user_data: UserData):
    task_id: str = call.data.split("|")[1]
    print(f'{task_id=}')

    # Редактируем сообщение - загрузка статуса
    splited_msg_text = call.message.text.split('\n')
    task_status_processing = splited_msg_text[-1]
    splited_msg_text[-1] = "..."
    new_msg_text = '\n'.join(splited_msg_text)
    try:
        await call.message.edit_text(new_msg_text, reply_markup=call.message.reply_markup)
    except:
        pass

    task: TaskData | None = await tryon_service.get_task(task_id=task_id, user_id=user_data.id)

    print(f'{task=}')

    if not task or task.task_status == TaskStatus.processing or task.task_status == TaskStatus.submitted:
        splited_msg_text = call.message.text.split('\n')
        splited_msg_text[-1] = task_status_processing
        new_msg_text = '\n'.join(splited_msg_text)
        await call.message.edit_text(new_msg_text, reply_markup=call.message.reply_markup)

    elif task.task_status == TaskStatus.failed:
        message_text = await get_localization_text(
            key="tryon_failed", language=user_data.language
        )
        await call.message.edit_text(message_text, reply_markup=call.message.reply_markup)

    elif task.task_status == TaskStatus.succeed:
        await call.message.delete()
        await call.message.answer_photo(photo=task.task_result.images[0].url)
        await try_on_start(call, user_data)
