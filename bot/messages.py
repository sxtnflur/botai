from caching.redis_caching import default_cached
from db.crud import get_user_request_or_token, get_user_language, get_cloth_categories_first_level
from db.database import connection
from db.sql_models.models import User, Rate, Localization, UserGroupRequests, Model, \
    ClothCategory
from services import tryon_service
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import load_only, selectinload
from bot.utils.messages import get_time_to_datetime, get_message
from services import get_rate_service

pre_ai_generation_anthropic = dict(
    message_key="pre_ai_generation",
     inline_keyboard=[
         [{"text": "back",
           "callback_data": "chooseAssistant|creative_assistant|not_delete"}]
     ],
     inline_keyboard_keys=["back"]
)

pre_ai_generation_gpt = dict(
        message_key="pre_ai_generation",
     inline_keyboard=[
         [{"text": "back",
           "callback_data": "chooseAssistant|creative_assistant|not_delete"}]
     ],
     inline_keyboard_keys=["back"]
)

cant_use_model_anymore = dict(
    message_key="cant_use_model_anymore",
    inline_keyboard=[
        [{"text": "back", "callback_data": "change_assistant"}]
    ],
    inline_keyboard_keys=["back"]
)

choose_sex_message = dict(
    message_key="choose_sex",
    inline_keyboard=[
        [{"text": "sex_male", "callback_data": "choose_sex|M"}],
        [{"text": "sex_female", "callback_data": "choose_sex|F"}]
    ],
    inline_keyboard_keys=["sex_male", "sex_female"]
)

settings_message = dict(
    message_key="settings_message",
    inline_keyboard=[
        [{"text": "change_language_btn", "callback_data": "change_language"}],
        [{"text": "back", "callback_data": "chooseAssistant|assistant"}]
    ],
    inline_keyboard_keys=["back", "change_language_btn"]
)

async def get_main_menu(user_id: int, language: str):
    rate_service = await get_rate_service()
    user = await rate_service.get_user_rate(user_id=user_id, translate_by_language=language)
    print(f'{user=}')

    requests_text = []
    for rg in user.requests_groups:
        requests = {"requests": rg.requests}
        for model in rg.models:
            requests.setdefault("name", []).append(model.name)

        requests_text.append(f"<b>{', '.join(requests.get('name'))}</b>: {requests.get('requests')}")

    if requests_text:
        requests_text = "\n".join(requests_text)
    else:
        requests_text = "❌"


    inline_keyboard = [
        [{"text": "get_recommendation", "callback_data": f"ai_action|assistant|1"}],
        [{"text": "send_my_photo", "callback_data": f"ai_action|assistant|2"},
         {"text": "send_look_photos",
          "callback_data": f"ai_action|assistant|3"}],
        [{"text": "btn_try_on_start", "callback_data": "try_on_start"}],
        [{"text": "wardrobe", "callback_data": "wardrobe|all"}],
        [{"text": "my_threads", "callback_data": "threads|1|0|10"}],
        [{"text": "btn_settings", "callback_data": "settings"}],
        [{"text": "btn_rates", "callback_data": f"rates|assistant"}]
    ]

    inline_keyboard_keys = ["get_recommendation", "send_my_photo", "send_look_photos",
                            "change_assistant", "btn_rates", "btn_settings", "my_threads",
                            "wardrobe", "btn_try_on_start"]

    if user.rate_id and user.rate_date_end:
        user_rate_data = dict(rate_date_end=user.rate_date_end,
                              my_rate=user.rate.name,
                              max_tokens=user.rate.max_tokens)

        message = await get_message(
            message_key="restart_message_rate",
            language=language,
            inline_keyboard=inline_keyboard,
            inline_keyboard_keys=inline_keyboard_keys
        )
        time_to_end_rate = get_time_to_datetime(_datetime=user.rate_date_end,
                                                language=language)
        if not time_to_end_rate:
            user_rate_data["rate_date_end"] = "❌"
        else:
            user_rate_data["rate_date_end"] = time_to_end_rate

        message["text"] = message["text"].format(
            **user_rate_data,
            requests=requests_text
        )

    else:
        message = await get_message(
            message_key="restart_message",
            language=language,
            inline_keyboard=inline_keyboard,
            inline_keyboard_keys=inline_keyboard_keys
        )
        message["text"] = message["text"].format(
            requests=requests_text
        )
    return message



@connection
async def get_main_menu_message(session, telegram_id: int, language: str, assistant_type: str = "assistant"):
    stmt = f"""
        SELECT u.rate_date_end, u.rate_requests, l.{language} AS my_rate,
        COALESCE(utm.tokens, 0), am.assistant_type, rates.max_tokens
        FROM users u
        
        LEFT JOIN rates ON rates.id = u.rate_id
        LEFT JOIN localization l ON l.key = rates.name_id
        LEFT JOIN users_tokens_models utm ON utm.user_id = u.id
        LEFT JOIN ai_models am ON utm.model_id = am.id
        
        
        WHERE u.telegram_id = :telegram_id
        GROUP BY am.assistant_type, u.id, l.{language}, utm.tokens, rates.max_tokens
    """

    assistants = {}
    user_rate_data = {}
    print(stmt)
    result = await session.execute(text(stmt), dict(telegram_id=telegram_id))
    for row in result:
        rate_date_end, rate_requests, my_rate, tokens, assistant_type, max_tokens = row
        user_rate_data.update(rate_date_end=rate_date_end, my_rate=my_rate,
                              rate_requests=rate_requests, max_tokens=max_tokens)
        assistants[assistant_type] = tokens

    print(assistants)
    print(user_rate_data)

    # inline_keyboard, inline_keyboard_keys = await create_buttons_assistants(telegram_id=telegram_id)

    inline_keyboard = [
                          [{"text": "get_recommendation", "callback_data": f"ai_action|{assistant_type}|recommend"}],
                          [{"text": "send_my_photo", "callback_data": f"ai_action|{assistant_type}|send_my_photo"},
                          {"text": "send_look_photos",
                            "callback_data": f"ai_action|{assistant_type}|send_look_photos"}],
                          # [{"text": "change_assistant", "callback_data": "change_assistant"}],
                          [{"text": "btn_settings", "callback_data": "settings"}],
                          [{"text": "btn_rates", "callback_data": f"rates|{assistant_type}"}]
                      ]
    inline_keyboard_keys = ["get_recommendation", "send_my_photo", "send_look_photos",
                            "change_assistant", "btn_rates", "btn_settings"]

    if user_rate_data.get("my_rate") and user_rate_data.get("rate_date_end"):
        message = await get_message(
            message_key="restart_message_rate",
            language=language,
            inline_keyboard=inline_keyboard,
            inline_keyboard_keys=inline_keyboard_keys
        )
        time_to_end_rate = get_time_to_datetime(_datetime=user_rate_data.pop("rate_date_end"),
                                                language=language)
        if not time_to_end_rate:
            user_rate_data["rate_date_end"] = "❌"
        else:
            user_rate_data["rate_date_end"] = time_to_end_rate

        message["text"] = message["text"].format(
            **assistants,
            **user_rate_data
        )

    else:
        message = await get_message(
            message_key="restart_message",
            language=language,
            inline_keyboard=inline_keyboard,
            inline_keyboard_keys=inline_keyboard_keys
        )
        message["text"] = message["text"].format(
            **assistants
        )

    return message


async def pre_ai_answer(telegram_id: int, model_id: int, assistant_type: str):
    can_use = await get_user_request_or_token(telegram_id, model_id=model_id, assistant_type=assistant_type)
    language = await get_user_language(telegram_id)
    if not can_use:
        return await get_message(
            message_key="cant_use_model_anymore",
            language=language,
            inline_keyboard=[
                [{"text": "back", "callback_data": "change_assistant"}]
            ],
            inline_keyboard_keys=["back"]
        )


@default_cached
async def get_message_tryon_select_cloth_cats(language: str):
    # Получаем кнопки категорий
    categories: list[ClothCategory] = await tryon_service.get_cloth_categories()
    print(f'{categories=}')

    inline_keyboard = [[]]
    inline_keyboard_keys = ["back"]
    for cat in categories:
        btn = {"text": cat.name, "callback_data": f"try_on_select_cat|{cat.id}"}
        inline_keyboard_keys.append(cat.name)

        if len(inline_keyboard[-1]) == 2:
            inline_keyboard.append([btn])
        else:
            inline_keyboard[-1].append(btn)
    inline_keyboard.append([{"text": "back", "callback_data": "chooseAssistant|assistant"}])

    return await get_message(
        message_key="try_on_select_cat",
        inline_keyboard=inline_keyboard,
        inline_keyboard_keys=inline_keyboard_keys,
        language=language
    )

