from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from db.crud import get_user_language, get_localization_text
from bot.handlers.try_on.try_on import TryOnStates
from bot.keyboards import create_kb_tryon_my_generated_models
from foreing_services.klingai_actions.schemas import TryOnClothModelSchema
from schemas.user import Gender, UserData
from services import tryon_service
from bot.utils.messages import get_message, send_message

router = Router()


@router.callback_query(F.data == "try_on_use_model")
async def try_on_use_model(call: CallbackQuery, state: FSMContext, user_data: UserData):
    data = await state.get_data()
    cloth_category_id = data.get("cloth_category_id")

    language = await get_user_language(telegram_id=call.from_user.id)

    message_data = await get_message(
        message_key="tryon_get_human_img",
        inline_keyboard=[
            [{"text": "try_on_create_new_model", "callback_data": "try_on_create_new_model"}],
            [{"text": "try_on_select_my_model", "callback_data": "try_on_select_my_model"}],
            [{"text": "back", "callback_data": f"try_on_select_cat|{cloth_category_id}"}]
        ],
        inline_keyboard_keys=["back", "try_on_create_new_model", "try_on_select_my_model"],
        language=language
    )
    await send_message(message_data=message_data, call=call)


@router.callback_query(F.data.startswith("try_on_select_my_model"))
async def try_on_select_my_model(call: CallbackQuery, user_data: UserData):
    offset = 0
    limit = 10
    try:
        offset = int(call.data.split("|")[1])
        limit = int(call.data.split("|")[2])
    except:
        pass

    kb = await create_kb_tryon_my_generated_models(user_id=user_data.id,
                                                   language=user_data.language,
                                                   offset=offset, limit=limit)
    text = await get_localization_text(key="tryon_select_your_model", language=user_data.language)
    await send_message(message_data={"text": text, "reply_markup": kb},
                       call=call)


@router.callback_query(F.data == "try_on_create_new_model")
async def try_on_create_new_model(call: CallbackQuery, user_data: UserData):
    message_data = await get_message(
        message_key="select_tryon_model_gender",
        inline_keyboard=[
            [{"text": "sex_male", "callback_data": "select_tryon_model_gender|male"}],
            [{"text": "sex_female", "callback_data": "select_tryon_model_gender|female"}],
            [{"text": "back", "callback_data": "try_on_use_model"}]
        ],
        inline_keyboard_keys=["sex_male", "sex_female", "back"],
        language=user_data.language
    )
    await send_message(message_data=message_data, call=call)


@router.callback_query(F.data.startswith("select_tryon_model_gender|"))
async def select_tryon_model_gender(call: CallbackQuery, state: FSMContext, user_data: UserData):
    gender = call.data.split("|")[1]
    await state.update_data(tryon_model_is_male=(gender == "male"))

    message_data = await get_message(
        message_key="tryon_write_prompt",
        inline_keyboard=[
            [{"text": "tryon_genmodel_skip_prompt", "callback_data": "tryon_genmodel_skip_prompt"}],
            [{"text": "back", "callback_data": "try_on_create_new_model"}]
        ],
        inline_keyboard_keys=["back", "tryon_genmodel_skip_prompt"],
        language=user_data.language
    )
    await send_message(message_data=message_data, call=call)
    await state.set_state(TryOnStates.generate_model_prompt)


@router.message(TryOnStates.generate_model_prompt, F.text)
async def tryon_genmodel_get_additional_prompt(m: Message, state: FSMContext, user_data: UserData):
    data = await state.get_data()
    tryon_model_is_male = data.get("tryon_model_is_male")
    model_gender = "male" if tryon_model_is_male else "female"

    await state.update_data(tryon_model_prompt=m.text)

    message_data = await get_message(
        message_key="check_tryon_gen_model_right",
        inline_keyboard=[
            [{"text": "try_on_start_gen_model", "callback_data": "try_on_start_gen_model"}],
            [{"text": "back", "callback_data": f"select_tryon_model_gender|{model_gender}"}]
        ],
        inline_keyboard_keys=["try_on_start_gen_model", "back"],
        language=user_data.language
    )
    message_data["text"] = message_data["text"].format(
        gender=("🙋‍♂️" if tryon_model_is_male else "🙋‍♀️"),
        additional_prompt=(m.text or "-")
    )

    await send_message(message_data, message=m)


@router.callback_query(F.data == "tryon_genmodel_skip_prompt")
async def tryon_genmodel_skip_prompt(call: CallbackQuery, state: FSMContext, user_data: UserData):
    data = await state.get_data()
    tryon_model_is_male = data.get("tryon_model_is_male")
    model_gender = "male" if tryon_model_is_male else "female"

    await state.update_data(tryon_model_prompt=None)

    message_data = await get_message(
        message_key="check_tryon_gen_model_right",
        inline_keyboard=[
            [{"text": "try_on_start_gen_model", "callback_data": "try_on_start_gen_model"}],
            [{"text": "back", "callback_data": f"select_tryon_model_gender|{model_gender}"}]
        ],
        inline_keyboard_keys=["try_on_start_gen_model", "back"],
        language=user_data.language
    )
    message_data["text"] = message_data["text"].format(
        gender=("🙋‍♂️" if tryon_model_is_male else "🙋‍♀️"),
        additional_prompt="-"
    )

    await send_message(message_data, call=call)


async def send_message_generated_model(call: CallbackQuery,
                                       tryon_model: TryOnClothModelSchema,
                                       back_call_data: str, language: str):
    message_data = await get_message(message_key="tryon_my_generated_model",
                                     inline_keyboard=[
                                         [{"text": "tryon_use_this_model",
                                           "callback_data": f"tryon_use_this_model|{tryon_model.id}"}],
                                         # [{"text": "tryon_retrieve_model",
                                         #   "callback_data": f"tryon_retrieve_model|{tryon_model.task_id}"}],
                                         [{"text": "back", "callback_data": back_call_data}]
                                     ],
                                     inline_keyboard_keys=["tryon_use_this_model", "back"],
                                     language=language
                                     )
    message_data["caption"] = message_data.pop("text")
    message_data["caption"] = message_data["caption"].format(
        created_at=tryon_model.created_at.strftime("%H:%M %d.%m.%Y"),
        gender=("🙋‍♂️" if tryon_model.is_male else "🙋‍♀️"),
        prompt=(tryon_model.prompt or "-")
    )
    await call.message.answer_photo(
        photo=tryon_model.model_image,
        **message_data,
        parse_mode="html"
    )


@router.callback_query(F.data == "try_on_start_gen_model")
async def try_on_generate_new_model(call: CallbackQuery, state: FSMContext, user_data: UserData):
    data = await state.get_data()
    tryon_model_is_male = data.get("tryon_model_is_male")
    additional_prompt: str | None = data.get("tryon_model_prompt")

    # Отправка сообщения с просьбой подождать ответа
    wait_message_data = await get_message(
        message_key="pre_ai_generation",
        inline_keyboard=[
            [{"text": "back", "callback_data": "chooseAssistant|assistant"}]
        ],
        inline_keyboard_keys=["back"],
        language=user_data.language
    )
    wait_message: Message = await send_message(message_data=wait_message_data, call=call)

    await call.bot.send_chat_action(chat_id=call.message.chat.id, action="upload_photo")

    await tryon_service.generate_image_model(
        user_id=user_data.id,
        gender=Gender.male if tryon_model_is_male else Gender.female,
        additional_prompt=additional_prompt,
        user_telegram_id=call.from_user.id,
        language=user_data.language
    )

    # # Отправка сообщения с генерированным фото модели
    # await wait_message.delete()
    # await send_message_generated_model(
    #     call=call,
    #     back_call_data="try_on_use_model",
    #     language=user_data.language,
    #     tryon_model=tryon_model
    # )


@router.callback_query(F.data.startswith("tryon_use_this_model|"))
async def tryon_use_this_model(call: CallbackQuery, state: FSMContext, user_data: UserData):
    human_image_model_id: int = int(call.data.split("|")[1])
    await state.update_data(human_image_model_id=human_image_model_id)

    # await state.update_data(human_photo=call.message.photo[-1].file_id)
    # await

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


@router.callback_query(F.data.startswith("tryon_my_generated_model|"))
async def tryon_my_generated_model(call: CallbackQuery, user_data: UserData):
    model_id = int(call.data.split("|")[1])
    model: TryOnClothModelSchema = await tryon_service.get_tryon_cloth_model(model_id)
    await send_message_generated_model(
        call=call, tryon_model=model,
        language=user_data.language, back_call_data="try_on_select_my_model"
    )