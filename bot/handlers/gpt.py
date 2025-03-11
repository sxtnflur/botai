from typing import List
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery
from db.crud import get_user_language
from bot.keyboards import get_kb_gpt
from bot.messages import pre_ai_generation_gpt
from bot.middleware import AlbumMiddleware
from schemas.gpt import TextResponse, ImageResponse, GPTResponseStatus
from schemas.user import UserData
from services.gpt import GPTService
from bot.utils.messages import send_message, get_message
from bot.utils.formatting import tg_photo_to_url, tg_photo_to_bytes

router = Router()
router.message.middleware(AlbumMiddleware())


gpt_service = GPTService()


class GPTStates(StatesGroup):
    chatting = State()


@router.callback_query(F.data.startswith("ai_action|assistant|"))
async def start_gpt(call: CallbackQuery, state: FSMContext, user_data: UserData):
    action_id = int(call.data.split("|")[2])
    inline_keyboard = [
        [{"text": "back", "callback_data": f"chooseAssistant|assistant"}]
    ]

    action = await gpt_service.get_gpt_assinstant(id=action_id)

    await state.update_data(action_id=action_id)
    await state.set_state(GPTStates.chatting)

    message_data = await get_message(
        message_key=action.action_description,
        inline_keyboard=inline_keyboard,
        inline_keyboard_keys=["back"],
        language=user_data.language
    )
    await send_message(call=call, message_data=message_data)



@router.message(GPTStates.chatting)
async def chatting(m: Message, album: List[Message], state: FSMContext, user_data: UserData):
    data = await state.get_data()
    action_id = data.get("action_id", 1)
    thread_id = data.get("thread_id")

    await m.bot.send_chat_action(
        chat_id=m.from_user.id,
        action="typing"
    )

    print(f'{action_id=}')
    if m.text:
         gpt_response: TextResponse = await gpt_service.prompt_by_text(
            user_id=user_data.id,
            action_id=action_id,
            text=m.text,
            thread_id=thread_id,
            language=user_data.language,
            is_admin=user_data.is_admin
        )
    elif album:
        photo_urls = []
        for album_msg in album:
            photo_urls.append(await tg_photo_to_url(album_msg))

        gpt_response: TextResponse = await gpt_service.prompt_by_images(
            user_id=user_data.id,
            action_id=action_id,
            images=photo_urls,
            thread_id=thread_id,
            language=user_data.language,
            is_admin=user_data.is_admin
        )
    elif m.photo:
        gpt_response: TextResponse = await gpt_service.prompt_by_image(
            user_id=user_data.id,
            action_id=action_id,
            caption=m.text,
            thread_id=thread_id,
            language=user_data.language,
            is_admin=user_data.is_admin,
            image_url=(await tg_photo_to_url(m))
        )
    elif m.voice:
        audio = await tg_photo_to_bytes(file_id=m.voice.file_id, bot=m.bot)
        gpt_response: TextResponse = await gpt_service.prompt_by_audio(
            user_id=user_data.id,
            action_id=action_id,
            audio=audio,
            thread_id=thread_id,
            language=user_data.language,
            is_admin=user_data.is_admin,
        )

    else:
        return

    if thread_id != gpt_response.thread_id:
        await state.update_data(thread_id=thread_id)

    if gpt_response.status == GPTResponseStatus.not_enough_tokens:
        # Нет токенов на запрос
        message_data = await get_message(
            message_key="cant_use_model_anymore",
            language=user_data.language,
            inline_keyboard=[
                [{"text": "back", "callback_data": "change_assistant"}]
            ],
            inline_keyboard_keys=["back"]
        )
        await send_message(message_data, message=m)

    elif gpt_response.status == GPTResponseStatus.succeed:
        reply_markup = await get_kb_gpt(user_data.language, action_id, image_again=False)
        await m.answer(text=gpt_response.answer_text,
                       reply_markup=reply_markup,
                       parse_mode="Markdown")


# @router.message(GPTStates.chatting)
# async def chatting(m: Message, album: List[Message], state: FSMContext):
#     data = await state.get_data()
#     action_id = data.get("action_id", 1)
#     thread_id = data.get("thread_id")
#     print("ACTION_ID", action_id)
#     print("THREAD_ID", thread_id)
#
#     await m.bot.send_chat_action(
#         chat_id=m.from_user.id,
#         action="typing"
#     )
#     user_reg_data = await get_user_registration_data(m.from_user.id)
#
#     # Определяем действие (text/vision)
#     action = await get_gpt_action(m)
#     await state.update_data(gpt_action=action)
#
#     if not user_reg_data.is_admin_bot:
#         model_and_requests = await minus_request_user(telegram_id=m.from_user.id, action=action)
#
#         if model_and_requests is None:
#             # Нет токенов на запрос
#             message_data = await get_message(
#                 message_key="cant_use_model_anymore",
#                 language=user_reg_data.language,
#                 inline_keyboard=[
#                     [{"text": "back", "callback_data": "change_assistant"}]
#                 ],
#                 inline_keyboard_keys=["back"]
#             )
#             await send_message(message_data, message=m)
#             return
#
#         model, requests_have = model_and_requests
#     else:
#         model = DEFAULT_ADMIN_GPT_MODEL
#
#     my_rate = await get_my_rate(telegram_id=m.from_user.id, values=[Rate.max_tokens])
#
#     assistant_id = ASSISTANT_IDS.get(action_id).get("id")
#     assistant_stream = AssistantStream(assistant_id=assistant_id,
#                                        thread_id=thread_id,
#                                        model=model,
#                                        max_tokens=my_rate.max_tokens,
#                                        action=action)
#
#     language_to_first_message = None
#     # Если нет текущего диалога, создаем новый
#     if not thread_id:
#         thread = await assistant_stream.create_new_thread(telegram_id=m.from_user.id,
#                                                           action_id=action_id)
#         await state.update_data(thread_id=thread.id)
#         thread_id = thread.id
#         assistant_stream.thread_id = thread_id
#         language_to_first_message = user_reg_data.language
#
#     # Делаем из сообщения content для chatgpt
#     content = await get_content_from_message(message=m, album=album, language=language_to_first_message)
#     print("CONTENT:", content)
#
#     check_message = await assistant_stream.check_user_content(content, user_reg_data.language)
#     if check_message:
#         return await m.answer(text=check_message,
#                               reply_markup=await create_kb_back(
#                                   language=user_reg_data.language,
#                                   callback_data="chooseAssistant|assistant|not_delete"
#                                 )
#                               )
#
#     # Пробуем дать название диалогу
#     await assistant_stream.create_chat_name(thread_id=thread_id, telegram_user_id=m.from_user.id)
#
#     # Создаем InlineKeyboard
#     reply_markup = await get_kb_gpt(user_reg_data.language, action_id, image_again=False)
#
#     await send_message_assistant(
#         content=content,
#         assistant_stream=assistant_stream,
#         message=m,
#         reply_markup=reply_markup
#     )


# @router.callback_query(F.data.startswith("show_image"))
# async def showImage_(call: CallbackQuery, state: FSMContext):
#
#     try:
#         is_again = call.data.split("|")[1]
#     except:
#         is_again = None
#
#     data = await state.get_data()
#     thread_id = data.get("thread_id")
#
#     language = await get_user_language(telegram_id=call.from_user.id)
#     await call.message.bot.send_chat_action(
#         chat_id=call.from_user.id,
#         action="upload_photo"
#     )
#
#     # Если запрос повторный, списываем токен
#     if is_again:
#         model_and_requests = await minus_request_user(telegram_id=call.from_user.id, action="generate_img")
#         if not model_and_requests:
#             # Нет токенов на запрос
#             message_data = await get_message(
#                 message_key="cant_use_model_anymore",
#                 language=language,
#                 inline_keyboard=[
#                     [{"text": "back", "callback_data": "change_assistant"}]
#                 ],
#                 inline_keyboard_keys=["back"]
#             )
#             return await send_message(message_data, call=call)
#
#
#     assistant_id = ASSISTANT_IDS.get(1).get("id")
#     # model = await get_model_by_action(action="generate_img", telegram_id=call.from_user.id)
#
#     assistant_stream = AssistantStream(
#         assistant_id=assistant_id,
#         thread_id=thread_id,
#         model="dall-e-3"
#     )
#
#     if not thread_id:
#         thread = await assistant_stream.create_new_thread(telegram_id=call.from_user.id)
#         await state.update_data(thread_id=thread.id)
#         assistant_stream.thread_id = thread.id
#
#         if call.message.text:
#             gpt_answer = call.message.text
#         else:
#             gpt_answer = call.message.caption
#
#         content = f"""
#         Сгенерируй картинку по данному тексту: {gpt_answer}
#         """
#     else:
#         content = "Сгенерируй картинку к твоему последнему сообщению"
#
#     reply_markup = await create_kb(
#         buttons=[
#             [{"text": "show_image", "callback_data": "show_image|again"}],
#             [{"text": "alternative_answer", "callback_data": "alternative_answer"}],
#             [{"text": "back", "callback_data": "chooseAssistant|assistant|not_delete"}]
#         ],
#         keys=["show_image", "alternative_answer", "back"],
#         language=language
#     )
#
#     await send_message_assistant(
#         content=content,
#         assistant_stream=assistant_stream,
#         message=call.message,
#         reply_markup=reply_markup
#     )


@router.callback_query(F.data.startswith("show_image"))
async def showImage_(call: CallbackQuery, user_data: UserData):
    if call.message.text:
        gpt_answer = call.message.text
    else:
        gpt_answer = call.message.caption

    # Отправляем сообщение с просьбой подождать
    warning_message_data = await get_message(**pre_ai_generation_gpt, language=user_data.language)
    warning_message = await call.message.answer(**warning_message_data)
    await call.message.bot.send_chat_action(
        chat_id=call.from_user.id,
        action="upload_photo"
    )

    image_response: ImageResponse = await gpt_service.generate_image(
        user_id=user_data.id, gpt_answer=gpt_answer,
        is_again=len(call.data.split("|")) > 1 and call.data.split("|")[1] == "again"
    )
    if image_response.status == GPTResponseStatus.not_enough_tokens:
        message_data = await get_message(
            message_key="cant_use_model_anymore",
            language=user_data.language,
            inline_keyboard=[
                [{"text": "back", "callback_data": "change_assistant"}]
            ],
            inline_keyboard_keys=["back"]
        )
        await warning_message.delete()
        return await send_message(message_data, call=call)

    elif image_response.status == GPTResponseStatus.succeed:
        # Создаем inline keyboard
        reply_markup = await get_kb_gpt(user_data.language, 1, image_again=True)

        # Удаляем предыдущие сообщения
        await warning_message.delete()
        await call.message.delete()

        # Отправляем новые сообщения - с фото и с предыдущим ответом с кнопками
        await call.message.answer_photo(photo=image_response.image_url)
        await call.message.answer(gpt_answer, reply_markup=reply_markup)


# @router.callback_query(F.data.startswith("show_image"))
# async def showImage_(call: CallbackQuery, state: FSMContext):
#
#     if call.message.text:
#         gpt_answer = call.message.text
#     else:
#         gpt_answer = call.message.caption
#
#     language = await get_user_language(telegram_id=call.from_user.id)
#
#     # Отправляем сообщение с просьбой подождать
#     warning_message_data = await get_message(**pre_ai_generation_gpt, language=language)
#     warning_message = await call.message.answer(**warning_message_data)
#     await call.message.bot.send_chat_action(
#         chat_id=call.from_user.id,
#         action="upload_photo"
#     )
#     action = "generate_img"
#
#     # Проверка на повторную генерацию
#     if len(call.data.split("|")) > 1 and call.data.split("|")[1] == "again":
#         # Если генерация - повторная, забираем токен и получаем модель
#         user_minus_request: UserMinusRequest = await gpt_service.minus_user_request(
#             telegram_id=call.from_user.id, action=action
#         )
#         model = user_minus_request.available_model
#         # model_and_requests = await minus_request_user(telegram_id=call.from_user.id, action=action)
#         if not user_minus_request.has_tokens:
#             message_data = await get_message(
#                 message_key="cant_use_model_anymore",
#                 language=language,
#                 inline_keyboard=[
#                     [{"text": "back", "callback_data": "change_assistant"}]
#                 ],
#                 inline_keyboard_keys=["back"]
#             )
#             await warning_message.delete()
#             return await send_message(message_data, call=call)
#         else:
#             # model, user_requests = model_and_requests
#             image_again = True
#     else:
#         image_again = False
#         # Если генерация - первичная, не забираем токен и только получаем модель
#         model = await get_model_by_action(telegram_id=call.from_user.id, action=action)
#
#     # Инициируем генератор изображений и генерируем изображения
#     gpt_image_generator = ChatGPTImageGenerator(model=model, action=action)
#     images = await gpt_image_generator.generate_images(prompt=gpt_answer, n=1)
#     print("IMAGES:", images)
#     photo = images[0]
#
#     # Создаем inline keyboard
#     reply_markup = await get_kb_gpt(language, 1, image_again=image_again)
#
#     # Удаляем предыдущие сообщения
#     await warning_message.delete()
#     await call.message.delete()
#
#     # Отправляем новые сообщения - с фото и с предыдущим ответом с кнопками
#     await call.message.answer_photo(photo=photo.url)
#     await call.message.answer(gpt_answer, reply_markup=reply_markup)

@router.callback_query(F.data=="alternative_answer")
async def alternative_text(call: CallbackQuery, state: FSMContext, user_data: UserData):
    data = await state.get_data()
    thread_id = data.get("thread_id")
    action_id = data.get("action_id")

    # Если нет диалога или action или action_id - просим повторить вопрос (создастся новый диалог)
    if not thread_id or not action_id:
        message_data = await get_message(
            message_key="repeat_your_message",
            inline_keyboard=[
                [{"text": "back", "callback_data": "chooseAssistant|assistant"}]
            ],
            inline_keyboard_keys=["back"],
            language=user_data.language
        )
        await call.message.answer(**message_data)
        await state.set_state(GPTStates.chatting)
        return

    text_response: TextResponse = await gpt_service.prompt_by_text(
        user_id=user_data.id,
        action_id=action_id,
        text="Попробуй ответить еще раз по-другому",
        thread_id=thread_id,
        language=user_data.language,
        is_admin=user_data.is_admin
    )
    if text_response.status == GPTResponseStatus.not_enough_tokens:
        # Нет токенов на запрос
        message_data = await get_message(
            message_key="cant_use_model_anymore",
            language=user_data.language,
            inline_keyboard=[
                [{"text": "back", "callback_data": "change_assistant"}]
            ],
            inline_keyboard_keys=["back"]
        )
        await send_message(message_data, call=call, not_delete=True)
        return

    elif text_response.status == GPTResponseStatus.succeed:
        reply_markup = await get_kb_gpt(user_data.language, 1)
        await call.message.answer(
            text=text_response.answer_text,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )

# @router.callback_query(F.data=="alternative_answer")
# async def alternative_text(call: CallbackQuery, state: FSMContext):
#     data = await state.get_data()
#     thread_id = data.get("thread_id")
#     action = data.get("gpt_action")
#     action_id = data.get("action_id")
#
#     language = await get_user_language(telegram_id=call.from_user.id)
#
#     # Если нет диалога или action или action_id - просим повторить вопрос (создастся новый диалог)
#     if not thread_id or not action or not action_id:
#         message_data = await get_message(
#             message_key="repeat_your_message",
#             inline_keyboard=[
#                 [{"text": "back", "callback_data": "chooseAssistant|assistant"}]
#             ],
#             inline_keyboard_keys=["back"],
#             language=language
#         )
#         await call.message.answer(**message_data)
#         await state.set_state(GPTStates.chatting)
#         return
#
#     # Забираем токен или возвращаем сообщение, что нет токенов
#     # model_and_requests = await minus_request_user(telegram_id=call.from_user.id, action=action)
#     # print(f"{model_and_requests=}")
#     user_minus_request: UserMinusRequest = await gpt_service.minus_user_request(
#         telegram_id=call.from_user.id, action=action
#     )
#
#     if not user_minus_request.has_tokens:
#         # Нет токенов на запрос
#         message_data = await get_message(
#             message_key="cant_use_model_anymore",
#             language=language,
#             inline_keyboard=[
#                 [{"text": "back", "callback_data": "change_assistant"}]
#             ],
#             inline_keyboard_keys=["back"]
#         )
#         await send_message(message_data, call=call, not_delete=True)
#         return
#
#     my_rate = await get_my_rate(telegram_id=call.from_user.id, values=[Rate.max_tokens])
#
#     # Получаем assistant_id и создаем объект AssistantStream
#     assistant_id = ASSISTANT_IDS.get(action_id).get("id")
#     assistant_stream = AssistantStream(
#         assistant_id=assistant_id,
#         thread_id=thread_id,
#         model=user_minus_request.available_model,
#         max_tokens=my_rate.max_tokens,
#         action=action
#     )
#
#     reply_markup = await get_kb_gpt(language, 1)
#
#     content = "Попробуй ответить еще раз по-другому"
#
#     await send_message_assistant(
#         content=content,
#         assistant_stream=assistant_stream,
#         message=call.message,
#         reply_markup=reply_markup
#     )


#
# # MY PHOTO
#
#
#
#
# @router.message(GPTStates.my_photo)
# async def get_my_photo(m: Message, state: FSMContext):
#
#     language = await get_user_language(m.from_user.id)
#     warning_message_data = await get_message(**pre_ai_generation_gpt, language=language)
#     warning_message = await m.answer(**warning_message_data)
#     await m.bot.send_chat_action(
#         chat_id=m.from_user.id,
#         action="typing"
#     )
#
#
#     gpt_action = await ChatGPTVision.get_gpt_action(key="my_photo", telegram_id=m.from_user.id)
#     if not gpt_action:
#         message_data = await get_message(**cant_use_model_anymore, language=language)
#         return send_message(message_data, message=m)
#
#     cant_user_message_data = await pre_ai_answer(telegram_id=m.from_user.id,
#                                                  model_id=gpt_action.id,
#                                                  assistant_type="assistant")
#     if cant_user_message_data:
#         await warning_message.delete()
#         return await send_message(cant_user_message_data, message=m)
#
#     photo_url = await tg_photo_to_url(m)
#
#     gpt_vision = ChatGPTVision(gpt_action)
#     answer_text = await gpt_vision.send_prompt_photo_url(
#         photo_url=photo_url,
#         caption=m.caption,
#         language=language
#     )
#
#     await warning_message.delete()
#     await m.answer(answer_text, parse_mode="Markdown", reply_markup=warning_message.reply_markup)
#     await state.clear()
#
#
# @router.message(GPTStates.photo_cloth_kit, F.photo)
# async def get_photo_clothes_kit(m: Message, album: List[Message], state: FSMContext):
#     language = await get_user_language(m.from_user.id)
#     warning_message_data = await get_message(**pre_ai_generation_gpt, language=language)
#     warning_message = await m.answer(**warning_message_data)
#     await m.bot.send_chat_action(
#         chat_id=m.from_user.id,
#         action="typing"
#     )
#
#     gpt_action = await ChatGPTVision.get_gpt_action(key="photo_cloth_kit", telegram_id=m.from_user.id)
#
#     cant_user_message_data = await pre_ai_answer(telegram_id=m.from_user.id,
#                                                  model_id=gpt_action.id,
#                                                  assistant_type="assistant")
#
#     if cant_user_message_data:
#         await warning_message.delete()
#         return await send_message(cant_user_message_data, message=m)
#
#     photo_urls = []
#     for album_msg in album:
#         photo_urls.append(await tg_photo_to_url(album_msg))
#
#     gpt = ChatGPTVision(gpt_action)
#     answer = await gpt.send_many_photo_urls(photo_urls=photo_urls, language=language)
#
#     await warning_message.delete()
#     await m.answer(answer, parse_mode="Markdown", reply_markup=warning_message.reply_markup)
#     await state.clear()