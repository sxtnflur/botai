from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from bot.keyboards import get_kb_wardrobe, combine_keyboards, create_kb, create_kb_cloth_categories, \
    get_inline_keyboard_cloth_categories
from bot.utils.formatting import tg_photo_to_bytes
from bot.utils.messages import get_message, send_message
from db.crud import get_localization_text
from schemas.user import UserData
from services import GPTService, VirtualTryOn

router = Router()

DEFAULT_LIMIT = 10


class WardrobeStates(StatesGroup):
    add_wardrobe_send_photo = State()
    add_wardrobe_add_name = State()



async def send_message_start_wardrobe(state: FSMContext, user_data: UserData,
                                      type_query: str,
                                      offset: int = 0,
                                      limit: int = DEFAULT_LIMIT,
                                      cloth_category_id: int | None = None,
                                      message: Message = None,
                                      call: CallbackQuery = None):
    await state.clear()
    kb = await get_kb_wardrobe(user_id=user_data.id,
                               offset=offset, limit=limit,
                               cloth_category_id=cloth_category_id
                               )

    inline_keyboard = []
    inline_keyboard_keys = ["all", "add_wardrobe", "by_cloth_category", "back"]

    if not cloth_category_id:
        inline_keyboard.append([{"text": "all", "callback_data": "wardrobe|all", "end_emoji": "✅"},
                                {"text": "by_cloth_category", "callback_data": "select_cloth_cat_for_we_filter"}])
    elif cloth_category_id:
        btn_name = "by_cloth_category"
        cloth_cat = await VirtualTryOn().get_cloth_category(cloth_category_id)
        if cloth_cat and cloth_cat.name:
            btn_name = cloth_cat.name
            inline_keyboard_keys.append(cloth_cat.name)


        print(f'{btn_name=}')

        inline_keyboard.append([{"text": "all", "callback_data": "wardrobe|all"},
                                {"text": btn_name, "callback_data": "select_cloth_cat_for_we_filter",
                                 "end_emoji": "✅"}])
    else:
        return

    message_data = await get_message(
        message_key="wardrobe_main_msg",
        inline_keyboard=inline_keyboard + [
            [{"text": "add_wardrobe", "callback_data": "add_wardrobe"}],
            [{"text": "back", "callback_data": "start"}]
        ],
        inline_keyboard_keys=inline_keyboard_keys,
        language=user_data.language
    )
    message_data["reply_markup"] = await combine_keyboards(
        kb.inline_keyboard, message_data["reply_markup"].inline_keyboard
    )
    await send_message(message_data=message_data,
                       call=call, message=message)


@router.callback_query(F.data.startswith("wardrobe|"))
async def start_wardrobe(call: CallbackQuery, state: FSMContext,
                       user_data: UserData):
    type_query = call.data.split("|")[1]

    offset = 0
    limit = DEFAULT_LIMIT
    cloth_category_id: int | None = None
    try:
        offset = int(call.data.split("|")[2])
        limit = int(call.data.split("|")[3])
        cloth_category_id = int(call.data.split("|")[4])
    except:
        pass

    await send_message_start_wardrobe(
        state=state, user_data=user_data,
        type_query=type_query, call=call,
        offset=offset, limit=limit,
        cloth_category_id=cloth_category_id
    )


@router.callback_query(F.data == "select_cloth_cat_for_we_filter")
async def select_cloth_cat_for_we_filter(call: CallbackQuery,
                                         user_data: UserData):
    kb = await create_kb_cloth_categories(
        callback_data_prefix=f"wardrobe|by_cloth_cat|0|{DEFAULT_LIMIT}",
        callback_data_back=f"wardrobe|all|0|{DEFAULT_LIMIT}",
        language=user_data.language
    )
    await call.message.edit_reply_markup(
        reply_markup=kb
    )


@router.callback_query(F.data.startswith("edit_we|"))
async def edit_we(call: CallbackQuery, user_data: UserData):
    we_id = int(call.data.split("|")[1])
    we = await GPTService().get_user_wardrobe_element(user_id=user_data.id,
                                                      wardrobe_element_id=we_id)
    kb = await create_kb(
        buttons=[
            [{"text": "del_wardrobe", "callback_data": f"del_wardrobe|{we_id}"}],
            [{"text": "back", "callback_data": "wardrobe|all"}]
        ],
        keys=["del_wardrobe", "back"],
        language=user_data.language
    )

    try:
        await call.message.delete()
    except:
        pass

    await call.message.answer_photo(
        caption=we.name,
        photo=we.image_url,
        reply_markup=kb
    )

@router.callback_query(F.data.startswith("del_wardrobe|"))
async def del_wardrobe(call: CallbackQuery, state: FSMContext, user_data: UserData):
    we_id: int = int(call.data.split("|")[1])
    await GPTService().delete_wardrobe_element(
        wardrobe_element_id=we_id, user_id=user_data.id
    )
    we_is_deleted_msg_text = await get_localization_text(
        key="wardrobe_element_is_deleted", language=user_data.language
    )
    await send_message(message_data={"text": we_is_deleted_msg_text},
                       call=call)
    await send_message_start_wardrobe(
        state=state, user_data=user_data, type_query="all",
        call=call
    )


@router.callback_query(F.data == "add_wardrobe")
async def add_wardrobe(call: CallbackQuery, state: FSMContext,
                       user_data: UserData):
    message_data = await get_message(
        message_key="add_wardrobe_send_photo",
        inline_keyboard=[[{"text": "back", "callback_data": "wardrobe|all"}]],
        inline_keyboard_keys=["back"],
        language=user_data.language
    )
    await send_message(message_data, call=call)
    await state.clear()
    await state.set_state(WardrobeStates.add_wardrobe_send_photo)

@router.message(WardrobeStates.add_wardrobe_send_photo, F.photo)
async def add_wardrobe_get_photo(m: Message, state: FSMContext,
                       user_data: UserData):
    await state.update_data(add_wardrobe_photo_file_id=m.photo[-1].file_id)

    inline_keyboard, inline_keyboard_keys = await get_inline_keyboard_cloth_categories(
        callback_data_prefix="add_wardrobe|cloth_cat",
        callback_data_back="wardrobe|all"
    )
    message_data = await get_message(
        message_key="add_wardrobe_select_cloth_cat",
        inline_keyboard=inline_keyboard,
        inline_keyboard_keys=inline_keyboard_keys,
        language=user_data.language
    )
    await m.answer_photo(
        photo=m.photo[-1].file_id,
        caption=message_data["text"],
        reply_markup=message_data["reply_markup"]
    )


@router.callback_query(F.data.startswith("add_wardrobe|cloth_cat|"))
async def add_wardrobe_select_cloth_cat(call: CallbackQuery,
                                        state: FSMContext,
                       user_data: UserData):
    cloth_category_id = int(call.data.split("|")[-1])
    await state.update_data(add_wardrobe_cloth_cat_id=cloth_category_id)
    message_data = await get_message(
        message_key="add_wardrobe_add_name",
        inline_keyboard=[[{"text": "back", "callback_data": "add_wardrobe"}]],
        inline_keyboard_keys=["back"],
        language=user_data.language
    )
    await send_message(message_data, call=call)
    await state.set_state(WardrobeStates.add_wardrobe_add_name)

@router.message(WardrobeStates.add_wardrobe_add_name, F.text)
async def addd_wardrobe_get_name(m: Message, state: FSMContext,
                                 user_data: UserData):
    data = await state.get_data()
    cloth_category_id = data.get("add_wardrobe_cloth_cat_id")
    image_file_id = data.get("add_wardrobe_photo_file_id")
    print(f'{image_file_id=}')
    image = await tg_photo_to_bytes(file_id=image_file_id,
                                    bot=m.bot)

    we_id: int = await GPTService().add_photo_cloth_to_wardrobe(
        cloth_category_id=cloth_category_id,
        name=m.text,
        user_id=user_data.id,
        image=image
    )
    await send_message_start_wardrobe(
        state, user_data, "all", message=m
    )