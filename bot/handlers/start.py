from aiogram import Router, F
from aiogram.filters import CommandStart, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, User as TgUser
from aiogram.utils.payload import decode_payload
from config import MAX_TRY_ON_A_DAY
from db.crud import check_admin_bot_payload
from bot.keyboards import create_kb_choose_language
from bot.messages import settings_message, choose_sex_message, get_main_menu
from foreing_services.fal_service.base import FalTryOn
from schemas.user import UserData, RegistrationStep, UpdateUser
from services.user import UserService
from bot.utils.messages import send_message, get_message

router = Router()

user_service = UserService()


async def get_start_message(state: FSMContext,
                            user_data: UserData):
    await state.clear()

    if user_data.registration_step == RegistrationStep.language:
        kb = await create_kb_choose_language()
        message: dict = await get_message(message_key="choose_language", language="ru")
        message["reply_markup"] = kb
    elif user_data.registration_step == RegistrationStep.sex:
        message: dict = await get_message(language=user_data.language, **choose_sex_message)
    else:
        message = await get_main_menu(user_id=user_data.id, language=user_data.language)

    return message


@router.message(CommandStart(deep_link=True), flags={"auth_off": True})
async def start_handler_deep_link(m: Message, command: CommandObject, state: FSMContext):
    if command.args == "hello":
        is_admin_bot = False
    else:
        payload = decode_payload(command.args)
        is_admin_bot: bool = await check_admin_bot_payload(payload=payload)

    user_data = await user_service.get_user_reg_data(
        telegram_id=m.from_user.id, first_name=m.from_user.first_name,
        last_name=m.from_user.last_name, username=m.from_user.username,
        is_admin_bot=is_admin_bot
    )
    message = await get_start_message(state=state,
                                      user_data=user_data)
    await send_message(message_data=message, message=m)


@router.message(CommandStart(deep_link=False))
async def start_handler(m: Message, state: FSMContext, user_data: UserData):
    message = await get_start_message(state=state, user_data=user_data)
    await send_message(message_data=message, message=m)


@router.callback_query(F.data == "start")
async def start_call_handler(call: CallbackQuery, state: FSMContext, user_data: UserData):
    message = await get_start_message(state=state, user_data=user_data)
    await send_message(message_data=message, call=call)


# @connection
# async def update_user_language(session, call: CallbackQuery, state: FSMContext):
#     codename = call.data.split("_")[1]
#     await session.execute(update(User).where(User.telegram_id==call.from_user.id).values(language=codename))
#     await session.commit()
#
#     message: dict = await get_message(
#         message_key="choose_sex",
#         language=codename,
#         inline_keyboard=[
#             [{"text": "sex_male", "callback_data": "choose_sex|M"}],
#             [{"text": "sex_female", "callback_data": "choose_sex|F"}]
#         ],
#         inline_keyboard_keys=["sex_male", "sex_female"]
#     )
#     await send_message(message_data=message, call=call)

@router.callback_query(F.data.startswith("choose_language|"))
async def chooseLanguage_(call: CallbackQuery, state: FSMContext):
    language = call.data.split("|")[1]
    is_registration = int(call.data.split("|")[2])
    await user_service.update_user_data_by_telegram_id(telegram_id=call.from_user.id,
                                                       updates=UpdateUser(language=language))

    if is_registration:
        message_data: dict = await get_message(language=language, **choose_sex_message)
    else:
        message_data: dict = await get_message(
            language=language, **settings_message
        )

    await send_message(message_data=message_data, call=call)


@router.callback_query(F.data.startswith("chooseAssistant|"))
async def chooseAssistant(call: CallbackQuery, state: FSMContext, user_data: UserData):
    not_delete = False
    try:
        additional_text = call.data.split("|")[2]
        if additional_text == "not_delete":
            not_delete = True
    except:
        pass
    message_data = await get_start_message(state=state, user_data=user_data)

    await send_message(message_data=message_data, call=call, not_delete=not_delete)


@router.callback_query(F.data == "change_assistant")
async def change_assistant(call: CallbackQuery, user_data: UserData):
    message = await get_main_menu(user_id=user_data.id, language=user_data.language)
    await send_message(message_data=message, call=call)


@router.callback_query(F.data.startswith("choose_sex|"))
async def choose_sex(call: CallbackQuery, user_data: UserData):
    sex = call.data.split("|")[1]
    language, is_admin = await user_service.update_user_data_by_telegram_id(
        telegram_id=call.from_user.id,
        returning=["language", "is_admin_bot"],
        updates=UpdateUser(sex=sex)
    )
    message = await get_main_menu(user_id=user_data.id, language=language)
    await send_message(message_data=message, call=call)


