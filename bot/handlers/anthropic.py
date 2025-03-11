from typing import List

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery
from foreing_services.claud_actions.main import AnthropicAPI
from db.crud import get_user_language
from foreing_services.gpt_actions.image_generator import ChatGPTImageGenerator
from bot.keyboards import create_kb
from bot.messages import pre_ai_generation_anthropic, pre_ai_answer
from bot.middleware import AlbumMiddleware
from bot.utils.messages import get_message, send_message
from bot.utils.formatting import tg_photo_to_b64

router = Router()
router.message.middleware(AlbumMiddleware())

class AnthropicStates(StatesGroup):
    text = State()
    my_photo = State()
    photo_cloth_kit = State()


@router.callback_query(F.data.startswith("ai_action|creative_assistant|"))
async def start_claud(call: CallbackQuery, state: FSMContext):
    action = call.data.split("|")[2]
    inline_keyboard = [
        [{"text": "back", "callback_data": f"chooseAssistant|creative_assistant"}]
    ]

    if action == "recommend":
        message_key = "get_recommendation_description"
        await state.set_state(AnthropicStates.text)
    elif action == "send_my_photo":
        message_key = "send_my_photo_description"
        await state.set_state(AnthropicStates.my_photo)
    elif action == "send_look_photos":
        message_key = "send_look_photos_description"
        await state.set_state(AnthropicStates.photo_cloth_kit)
    else:
        return

    language = await get_user_language(telegram_id=call.from_user.id)

    message_data = await get_message(
        message_key=message_key,
        inline_keyboard=inline_keyboard,
        inline_keyboard_keys=[message_key, "back"],
        language=language
    )
    await send_message(call=call, message_data=message_data)


@router.message(AnthropicStates.text, F.text)
async def get_anth_text(m: Message, state: FSMContext):
    language = await get_user_language(telegram_id=m.from_user.id)
    warning_message_data = await get_message(**pre_ai_generation_anthropic, language=language)
    warning_message = await m.answer(**warning_message_data)
    await m.bot.send_chat_action(
        chat_id=m.from_user.id,
        action="typing"
    )


    action = await AnthropicAPI.get_gpt_action(key="text", telegram_id=m.from_user.id)
    print(action)

    cant_user_message_data = await pre_ai_answer(telegram_id=m.from_user.id,
                                                 model_id=action.id, assistant_type="assistant")

    if cant_user_message_data:
        await warning_message.delete()
        return await send_message(cant_user_message_data, message=m)

    anth = AnthropicAPI(action)
    answer_text = await anth.send_text_prompt(prompt=m.text, language=language)

    kb = await create_kb(
        buttons=[
            [{"text": "show_image", "callback_data": "show_image_anthropic"}],
            [{"text": "alternative_answer", "callback_data": "alternative_answer_anthropic"}],
            [{"text": "back", "callback_data": "chooseAssistant|creative_assistant|not_delete"}]
        ],
        keys=["show_image", "alternative_answer", "back"],
        language=language
    )

    # if m.photo:
    #     image_url = await tg_photo_to_b64(message=m)
    #     answer_text = anth.send_image_prompt(image_url, prompt=m.caption)
    await warning_message.delete()
    await m.answer(str(answer_text), reply_markup=kb, parse_mode="Markdown")


@router.callback_query(F.data.startswith("show_image_anthropic"))
async def show_image_anthropic(call: CallbackQuery, state: FSMContext):
    if call.message.text:
        gpt_answer = call.message.text
    else:
        gpt_answer = call.message.caption

    language = await get_user_language(telegram_id=call.from_user.id)
    warning_message_data = await get_message(**pre_ai_generation_anthropic, language=language)
    warning_message = await call.message.answer(**warning_message_data)
    await call.message.bot.send_chat_action(
        chat_id=call.from_user.id,
        action="upload_photo"
    )

    action = await ChatGPTImageGenerator.get_gpt_action(telegram_id=call.from_user.id,
                                                                            assistant_type="all")
    print("ACTION:", action)


    try:
        second_data = call.data.split("|")[1]
        if second_data == "again":
            cant_user_message_data = await pre_ai_answer(telegram_id=call.from_user.id,
                                                         model_id=action.id,
                                                         assistant_type="creative_assistant")
            if cant_user_message_data:
                await warning_message.delete()
                return await send_message(cant_user_message_data, call=call)
    except:
        pass


    gpt_image_generator = ChatGPTImageGenerator(action)
    images = gpt_image_generator.generate_images(prompt=gpt_answer, n=1)
    print("IMAGES:", images)
    photo = images[0]
    # media_group = []
    # for i, image in enumerate(images):
    #     caption = None
    #     if not i:
    #         caption = gpt_answer
    #
    #     media_group.append(
    #         InputMediaPhoto(media=image.url, caption=caption)
    #     )


    kb = await create_kb(
        buttons=[
            [{"text": "show_image_again", "callback_data": "show_image_anthropic|again"}],
            [{"text": "alternative_answer", "callback_data": "alternative_answer_anthropic"}],
            [{"text": "back", "callback_data": "chooseAssistant|creative_assistant|not_delete"}]
        ],
        keys=["show_image_again", "alternative_answer", "back"],
        language=language
    )
    await warning_message.delete()
    await call.message.delete()

    await call.message.answer_photo(photo=photo.url)
    await call.message.answer(gpt_answer, reply_markup=kb)

@router.callback_query(F.data=="alternative_answer_anthropic")
async def alternative_answer_anthropic(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user_question = data.get("user_question")

    language = await get_user_language(telegram_id=call.from_user.id)

    if not user_question:
        message_data = await get_message(
            message_key="repeat_your_message",
            inline_keyboard=[
                [{"text": "back", "callback_data": "chooseAssistant|creative_assistant"}]
            ],
            inline_keyboard_keys=["back"],
            language=language
        )
        await call.message.answer(**message_data)
        await state.set_state(AnthropicStates.text)
        return

    warning_message_data = await get_message(**pre_ai_generation_anthropic, language=language)
    warning_message = await call.message.answer(**warning_message_data)
    await call.message.bot.send_chat_action(
        chat_id=call.from_user.id,
        action="typing"
    )

    action = await AnthropicAPI.get_gpt_action(key="text", telegram_id=call.from_user.id)
    print(action)

    cant_user_message_data = await pre_ai_answer(telegram_id=call.from_user.id,
                                                 model_id=action.id,
                                                 assistant_type="creative_assistant")

    if cant_user_message_data:
        await warning_message.delete()
        return await send_message(cant_user_message_data, call=call)


    anth = AnthropicAPI(action)
    answer_text = await anth.send_text_prompt(prompt=user_question, language=language)

    await state.update_data(gpt_answer=answer_text, user_question=user_question)

    user_language = await get_user_language(telegram_id=call.from_user.id)
    kb = await create_kb(
        buttons=[
            [{"text": "show_image", "callback_data": "show_image_anthropic"}],
            [{"text": "alternative_answer", "callback_data": "alternative_answer_anthropic"}],
            [{"text": "back", "callback_data": "chooseAssistant|creative_assistant|not_delete"}]
        ],
        keys=["show_image", "alternative_answer", "back"],
        language=user_language
    )
    await warning_message.delete()
    await call.message.answer(answer_text, reply_markup=kb, parse_mode="Markdown")




@router.message(AnthropicStates.my_photo, F.photo)
async def get_my_photo_anthropic(m: Message, state: FSMContext):

    language = await get_user_language(m.from_user.id)
    warning_message_data = await get_message(**pre_ai_generation_anthropic, language=language)
    warning_message = await m.answer(**warning_message_data)
    await m.bot.send_chat_action(
        chat_id=m.from_user.id,
        action="typing"
    )

    action = await AnthropicAPI.get_gpt_action(key="my_photo", telegram_id=m.from_user.id)

    anth = AnthropicAPI(action)
    image_b64 = await tg_photo_to_b64(message=m)
    answer_text = await anth.send_image_prompt(image_b64, prompt=m.caption, language=language)

    await warning_message.delete()
    await m.answer(answer_text, parse_mode="Markdown", reply_markup=warning_message.reply_markup)
    await state.clear()


@router.message(AnthropicStates.photo_cloth_kit, F.photo)
async def get_photo_clothes_kit(m: Message, album: List[Message], state: FSMContext):
    language = await get_user_language(m.from_user.id)
    warning_message_data = await get_message(message_key="pre_ai_generation",
                                             language=language,
                                             inline_keyboard=[
                                                 [{"text": "back", "callback_data": "chooseAssistant|assistant|not_delete"}]
                                             ],
                                             inline_keyboard_keys=["back"])
    warning_message = await m.answer(**warning_message_data)
    await m.bot.send_chat_action(
        chat_id=m.from_user.id,
        action="typing"
    )

    action = await AnthropicAPI.get_gpt_action(key="photo_cloth_kit", telegram_id=m.from_user.id)

    cant_user_message_data = await pre_ai_answer(telegram_id=m.from_user.id,
                                                 model_id=action.id,
                                                 assistant_type="creative_assistant")

    if cant_user_message_data:
        await warning_message.delete()
        return await send_message(cant_user_message_data, message=m)

    photos_b64 = []
    for album_msg in album:
        photos_b64.append(await tg_photo_to_b64(album_msg))

    anth = AnthropicAPI(action)
    answer = await anth.send_many_photo_urls(photo_images_b64=photos_b64, language=language)

    await warning_message.delete()
    await m.answer(answer, parse_mode="Markdown", reply_markup=warning_message.reply_markup)
    await state.clear()