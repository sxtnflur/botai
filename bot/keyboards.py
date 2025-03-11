import datetime
from typing import List
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from caching.redis_caching import default_cached
from config import ACTIONS
from db.crud import get_localization_texts
from db.database import connection
from db.schemas.gpt import ThreadSchema
from db.schemas.try_on import TryonPhotoSchema, ClothCategorySchema
from db.sql_models.models import Localization, Language, User
from foreing_services.klingai_actions.schemas import TryOnClothModelSchema
from schemas.rate import RateShortSchema, RateSchema
from services import gpt_service, rate_service, tryon_service, GPTService
from sqlalchemy import select, label

btn_gpt_start = "Получить рекомендацию (GPT-4o-mini)"
btn_gpt_4o_start = "Получить рекомендацию (GPT-4o)"
btn_gpt_send_photo = "Отправить свое фото"
btn_gpt_send_photo_clothes_kit = "Отправить комплект одежды"


button_back = {
    "en": "Back",
    "ru": "Назад",
    "uz": "Назад"
}

main_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="")]
    ]
)


gpt_text_answer_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Показать образ", callback_data="show_image")],
    [InlineKeyboardButton(text="Другой ответ", callback_data="alternative_text")]
])

gpt_text_answer_kb_4o = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Показать образ", callback_data="show_image_4o")],
    [InlineKeyboardButton(text="Другой ответ", callback_data="alternative_text_4o")]
])

# async def get_gpt_models_kb(models: list):
#     gpt_models_kb = InlineKeyboardBuilder()
#     for model in models:
#         gpt_models_kb.button(text=)

async def create_kb_from_texts(buttons: list[list[dict]], texts: dict) -> InlineKeyboardMarkup:

    inline_keyboard = []
    for btns in buttons:
        new_btns = []
        for btn in btns:
            btn = btn.copy()
            key_btn = btn.get("text")
            btn["text"] = texts.get(key_btn)

            if btn.get("end_emoji"):
                btn["text"] += " " + btn.pop("end_emoji")
            print(btn)
            try:
                new_btns.append(InlineKeyboardButton(**btn))
            except Exception as e:
                print(e)
                continue

        inline_keyboard.append(new_btns)
    print(inline_keyboard)
    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)

@connection
async def create_kb(session, buttons: list, keys: list, language: str) -> InlineKeyboardMarkup:
    texts = await session.execute(
        select(
            Localization.key, label('text', getattr(Localization, language))
        ).filter(Localization.key.in_(keys))
    )
    texts = {text.key: text.text for text in texts}
    return await create_kb_from_texts(buttons, texts)


async def create_kb_no_translate(buttons: list):
    inline_keyboard = []
    for btns in buttons:
        new_btns = []
        for btn in btns:
            try:
                new_btns.append(InlineKeyboardButton(**btn))
            except Exception as e:
                print(e)
                continue
        inline_keyboard.append(new_btns)
    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)

async def get_btn_back(language, callback_data):
    return InlineKeyboardButton(text=button_back.get(language), callback_data=callback_data)

@default_cached
@connection
async def create_kb_choose_language(session, back_callback_data: str = None, language: str = None,
                                    is_registration: int = 1):
    languages = await session.execute(select(Language).order_by(Language.ordering))
    kb = InlineKeyboardBuilder()

    i = 0
    for lang in languages.scalars():
        kb.button(text=lang.name, callback_data=f"choose_language|{lang.codename}|{is_registration}")
        i += 1

    if back_callback_data and language:
        kb.add(await get_btn_back(language, callback_data=back_callback_data))

    adjust = [2] * (i // 2)
    kb.adjust(*adjust, 1)
    return kb.as_markup()


def can_user_use_ai(user: User):
    return user.rate_date_end > datetime.datetime.now() or user.tokens > 0

async def create_kb_back(language: str, callback_data: str):
    return await create_kb(
        language=language,
        buttons=[
            [{"text": "back", "callback_data": callback_data}]
        ],
        keys=["back"]
    )

# @connection
# async def create_buttons_rates(session, user: User, assistant_type):
#     stmt = select(Rate.id, Rate.name_id,
#                   # label('name', getattr(Localization, user.language)),
#                   label('is_mine', Rate.id == user.rate_id)).order_by(Rate.id)
#     print(stmt)
#     result = await session.execute(stmt)
#     buttons = []
#     keys = ["back"]
#     my_rate = None
#     for rate in result:
#         keys.append(rate.name_id)
#         btn_data = {"text": rate.name_id, "callback_data": f"choose_rate|{rate.id}"}
#         if rate.is_mine:
#             btn_data["end_emoji"] = "✅"
#             my_rate = rate
#
#         buttons.append([btn_data])
#
#     if assistant_type == "no":
#         buttons.append([{"text": "back", "callback_data": f"change_assistant"}])
#     else:
#         buttons.append([{"text": "back", "callback_data": f"chooseAssistant|{assistant_type}"}])
#     return buttons, keys, my_rate

async def create_buttons_rates(my_rate_id: int):
    rates: List[RateShortSchema] = await rate_service.get_rates(user_rate_id=my_rate_id)
    buttons = []
    keys = ["back"]
    my_rate_name_id = None
    for rate in rates:
        keys.append(rate.name)
        btn_data = {"text": rate.name, "callback_data": f"choose_rate|{rate.id}"}

        if rate.is_mine:
            btn_data["end_emoji"] = "✅"
            my_rate_name_id = rate.name

        buttons.append([btn_data])
    buttons.append([{"text": "back", "callback_data": "chooseAssistant|assistant"}])
    return buttons, keys, my_rate_name_id



async def create_buttons_payways_rate(rate: RateSchema):
    btns = []

    # if rate.price_rub:
    #     pass
    # if rate.price_usd:
    #     pass
    if rate.price_uzs:
        btns.append([{"text": f"CLICK ({rate.price_uzs} UZS)", "callback_data": f"pay|rate|{rate.id}|click"}])
    if rate.price_stars:
        btns.append([{"text": f"Telegram Stars ({rate.price_stars})",
                      "callback_data": f"pay|rate|{rate.id}|stars"}])

    return btns



# THREADS LIST
async def create_kb_threads(user_id: int, language: str, action_id: int,
                            offset: int = 0, limit: int = 10):
    print(f"{action_id=}")
    print(f"{offset=}")
    print(f"{limit=}")
    threads: List[ThreadSchema] = await gpt_service.get_user_gpt_threads(user_id, action_id, offset, limit)
    # threads = await get_user_threads(telegram_id=telegram_id, action_id=action_id,
    #                                  offset=offset, limit=limit)
    inline_keyboard = [[]]
    threads_count = 0
    for thread in threads:
        threads_count += 1

        if thread.name:
            name = thread.name
        else:
            name = thread.created_at.strftime("%H:%M %d.%m.%Y")

        print(f"{name=}")

        btn = InlineKeyboardButton(text=name, callback_data=f"get_thread|{thread.id}")

        if len(inline_keyboard[-1]) == 2:
            inline_keyboard.append([btn])
        else:
            inline_keyboard[-1].append(btn)

    # Пагинация
    pagination_btns = []
    if offset > 0:
        pagination_btns.append(InlineKeyboardButton(text="◀️",
                                                    callback_data=f"threads|{action_id}|{offset-limit}|{limit}"))
    if limit == threads_count:
        pagination_btns.append(InlineKeyboardButton(text="▶️",
                                                    callback_data=f"threads|{action_id}|{offset+limit}|{limit}"))
    if pagination_btns:
        inline_keyboard.append(pagination_btns)

    # Доп кнопки
    btn_texts = await get_localization_texts(
        language=language,
        keys=["get_recommendation", "send_my_photo", "send_look_photos", "back"])

    # Разделы
    # groups_btns = []
    for aid, key in ACTIONS.items():
        btn_text = btn_texts.get(key)
        if aid == action_id:
            btn_text += " ✅"
            btn_data = "-"
        else:
            btn_data = f"threads|{aid}|0|10"
        inline_keyboard.append([InlineKeyboardButton(text=btn_text, callback_data=btn_data)])
    # inline_keyboard.append(groups_btns)

    # Кнопка назад
    inline_keyboard.append([InlineKeyboardButton(text=btn_texts.get("back"), callback_data="change_assistant")])

    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)


async def get_kb_gpt(language: str, action_id: int, image_again: bool = False, btn_back_data: str|None = None):
    buttons = [
        [{"text": "alternative_answer", "callback_data": "alternative_answer"}],
        [{"text": "back", "callback_data": btn_back_data or "chooseAssistant|assistant|not_delete"}]
    ]
    keys = ["alternative_answer", "back"]

    if action_id == 1:
        if image_again:
            buttons.insert(0, [{"text": "show_image_again", "callback_data": "show_image|again"}])
            keys.append("show_image_again")
        else:
            buttons.insert(0, [{"text": "show_image", "callback_data": "show_image"}])
            keys.append("show_image")
    return await create_kb(
        buttons=buttons, keys=keys, language=language
    )



async def create_kb_tryon_my_generated_models(user_id: int,
                                              language: str,
                                              back_callback_data: str = "try_on_use_model",
                                              offset: int = 0,
                                              limit: int = 10
                                              ):
    max_len_prompt = 10

    tryon_models: List[TryOnClothModelSchema] = await tryon_service.get_user_tryon_cloth_models(user_id=user_id,
                                                                                                offset=offset,
                                                                                                limit=limit)
    inline_keyboard = [[]]
    for model in tryon_models:
        model: TryOnClothModelSchema
        created_at: str = model.created_at.strftime("%H:%M %d.%m.%Y")
        if model.prompt:
            if len(model.prompt) > max_len_prompt:
                prompt = model.prompt[:max_len_prompt] + "..."
            else:
                prompt = model.prompt
        else:
            prompt = ""

        btn_text = f"{'🙋‍♂' if model.is_male else '🙋‍♀'}{prompt}[{created_at}]"

        btn = InlineKeyboardButton(
            text=btn_text, callback_data=f"tryon_my_generated_model|{model.id}"
        )

        if len(inline_keyboard[-1]) == 2:
            inline_keyboard.append([btn])
        else:
            inline_keyboard[-1].append(btn)

    pagination_buttons = []
    if offset > 0:
        new_offset = offset - limit
        if new_offset < 0:
            new_offset = 0

        pagination_buttons.append(InlineKeyboardButton(text="<",
                                                       callback_data=f"try_on_select_my_model|{new_offset}|{limit}"))

    if len(tryon_models) == limit:
        new_offset = offset + limit
        pagination_buttons.append(InlineKeyboardButton(text=">",
                                                       callback_data=f"try_on_select_my_model|{new_offset}|{limit}"))
    if pagination_buttons:
        inline_keyboard.append(pagination_buttons)


    inline_keyboard.append([await get_btn_back(language=language, callback_data=back_callback_data)])

    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)



async def create_kb_tryon_my_photos(user_id: int, language: str,
                                    cloth_category_id: int,
                                    offset: int = 0, limit: int = 10):
    my_human_photos: List[TryonPhotoSchema] = await tryon_service.get_tryon_my_photos(
        user_id, offset, limit
    )
    print(f'{my_human_photos=}')
    print(f'{offset=}')
    print(f'{limit=}')

    inline_keyboard = [[]]
    for p in my_human_photos:
        btn_name = p.created_at.strftime("%H:%M %d.%m.%Y")
        btn = InlineKeyboardButton(
            text=btn_name,
            callback_data=f"tryon_look_my_photo|{p.id}"
        )
        if len(inline_keyboard[-1]) == 2:
            inline_keyboard.append([btn])
        else:
            inline_keyboard[-1].append(btn)

    pagination_buttons = []
    if offset > 0:
        new_offset = offset - limit
        if new_offset < 0:
            new_offset = 0

        pagination_buttons.append(InlineKeyboardButton(text="<",
                                                       callback_data=f"try_on_use_my_photos|{new_offset}|{limit}"))

    if len(my_human_photos) == limit:
        new_offset = offset + limit
        pagination_buttons.append(InlineKeyboardButton(text=">",
                                                       callback_data=f"try_on_use_my_photos|{new_offset}|{limit}"))
    if pagination_buttons:
        inline_keyboard.append(pagination_buttons)

    inline_keyboard.append([
        await get_btn_back(language=language, callback_data=f"try_on_select_cat|{cloth_category_id}")
    ])
    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)


async def get_kb_wardrobe(user_id: int, offset: int = 0, limit: int = 10,
                          cloth_category_id: int | None = None) -> InlineKeyboardMarkup:
    gpt_service = GPTService()
    wardrobe_elements = await gpt_service.get_user_wardrobe_elements(
        user_id=user_id, offset=offset, limit=limit,
        cloth_category_id=cloth_category_id
    )

    inline_keyboard = [[]]
    for we in wardrobe_elements:
        btn = InlineKeyboardButton(
            text=we.name, callback_data=f"edit_we|{we.id}"
        )
        if len(inline_keyboard[-1]) == 2:
            inline_keyboard.append([btn])
        else:
            inline_keyboard[-1].append(btn)

    pagination = []
    if offset > 0:
        pagination.append(InlineKeyboardButton(
            text="<",
            callback_data=f"wardrobe|-|{offset-limit}|{limit}|" + str(cloth_category_id or ""))
        )

    if len(wardrobe_elements) == limit:
        pagination.append(InlineKeyboardButton(
            text=">",
            callback_data=f"wardrobe|-|{offset + limit}|{limit}|" + str(cloth_category_id or ""))
        )
    inline_keyboard.append(pagination)

    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)


async def get_inline_keyboard_cloth_categories(
        callback_data_prefix: str,
        callback_data_back: str,
) -> tuple[list[list[InlineKeyboardButton]], list[str]]:

    categories: list[ClothCategorySchema] = await tryon_service.get_cloth_categories()

    inline_keyboard = [[]]
    inline_keyboard_keys = ["back"]
    for cat in categories:
        btn = {"text": cat.name, "callback_data": f"{callback_data_prefix}|{cat.id}"}
        inline_keyboard_keys.append(cat.name)

        if len(inline_keyboard[-1]) == 2:
            inline_keyboard.append([btn])
        else:
            inline_keyboard[-1].append(btn)
    inline_keyboard.append([{"text": "back", "callback_data": callback_data_back}])
    return inline_keyboard, inline_keyboard_keys

async def create_kb_cloth_categories(callback_data_prefix: str,
        callback_data_back: str, language: str) -> InlineKeyboardMarkup:
    buttons, keys = await get_inline_keyboard_cloth_categories(
        callback_data_prefix, callback_data_back
    )
    return await create_kb(buttons, keys, language=language)

async def combine_keyboards(*inline_keyboards):
    print(f'{inline_keyboards=}')
    inline_keyboard = []
    for inl_kb in inline_keyboards:
        for inl_kb_ in inl_kb:
            inline_keyboard.append(inl_kb_)
    print(f'{inline_keyboard=}')
    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)