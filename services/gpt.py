from typing import List, Any

from caching.redis_caching import default_cached
from config import DEFAULT_ADMIN_GPT_MODEL, LANGUAGE_CAPTIONS, settings
from db.crud import minus_request_user, get_user_values, get_my_rate_values, get_model_by_action, \
    get_user_threads, get_thread, create_new_thread, update_thread, get_localization_text, get_all_assistants, \
    get_assistant, get_user_thread_id, add_wardrobe_elements, get_user_wardrobe_elements, get_user_wardrobe_element, \
    add_wardrobe_element, delete_wardrobe_element
from db.schemas.gpt import ThreadSchema, AddWardrobeElement
from foreing_services import ChatGPTImageGenerator, ChatGPT4, ChatGPTVision, Assistant, BunnyCDN
from openai.types.beta.threads import Message
from schemas.gpt import UserMinusRequest, GPTResponseStatus, TextResponse, ImageResponse, GPTAssistantSchema, \
    AssistantData, WardrobeElementResponse, WardrobeElementDeleted


class GPTService:
    file_manager = BunnyCDN

    async def minus_user_request(self, user_id: int, action: str, is_admin: bool) -> UserMinusRequest:
        model_and_requests = await minus_request_user(user_id=user_id, action=action)
        if model_and_requests is None:
            has_tokens = False
            model = None
        else:
            has_tokens = True
            model, requests_have = model_and_requests

        return UserMinusRequest(available_model=model, has_tokens=has_tokens)


    async def __before_send_content(self,
                          user_id: int,
                          is_admin: bool,
                          action_id: int) -> AssistantData | None:
        if is_admin:
            user_minus_request = UserMinusRequest(
                available_model=DEFAULT_ADMIN_GPT_MODEL,
                has_tokens=True
            )
            max_tokens = 2000
        else:
            user_minus_request: UserMinusRequest = await self.minus_user_request(user_id, "text", is_admin)
            if not user_minus_request.has_tokens:
                return

            # Получаем кол-во токенов максимально допустимое для тарифа пользователя
            max_tokens: int | None = await get_my_rate_values(user_id=user_id, values=["max_tokens"])
            if not max_tokens:
                max_tokens = settings.ai_trial_max_tokens

        assistant = await self.get_gpt_assinstant(id=action_id)

        return AssistantData(
            assistant_id=assistant.assistant_id,
            model=user_minus_request.available_model,
            max_tokens=max_tokens,
        )

    async def send_content_get_text(self,
                          user_id: int,
                          language: str,
                          is_admin: bool,
                          content: list,
                          action_id: int,
                          thread_id: str | None = None) -> TextResponse:
        wardrobe_elements = await self.get_user_wardrobe_elements(user_id)
        content += [
            {"type": "image_file",
             "image_file": {
                 "file_id": we.gpt_file_id,
                 "detail": "low"
                }
             } for we in wardrobe_elements
        ]

        print(f'{content=}')
        # NEW: thread_id - Один на пользователя
        # thread_id: str | None = await get_user_thread_id(user_id)

        assistant_data: AssistantData | None = await self.__before_send_content(
            user_id=user_id, is_admin=is_admin, action_id=action_id
        )
        if not assistant_data:
            return TextResponse(status=GPTResponseStatus.not_enough_tokens)

        print(f'{assistant_data.model_dump()=}')
        assistant = Assistant(**assistant_data.model_dump())

        # Если нет текущего диалога, создаем новый
        created_db_thread_id: int | None = None

        print(f"До создания: {thread_id=}")
        if not thread_id:
            thread_id = await assistant.create_new_thread()

            # NEW: thread_id - Один на пользователя
            created_db_thread_id: int = await create_new_thread(user_id=user_id, thread_id=thread_id,
                                                                action_id=action_id)
        print(f"После создания: {thread_id=}")
        # Проверяем сообщение
        check_message = await assistant.check_user_content(content)
        if check_message:
            text = await get_localization_text(key="ask_chatgpt_answer_text",
                                                   language=language)
            return TextResponse(
                status=GPTResponseStatus.succeed,
                answer_text=text,
                thread_id=thread_id,
                chat_name=None,
                created_db_thread_id=created_db_thread_id
            )

        # Пробуем дать название диалогу
        chat_name: str = await assistant.create_chat_name(thread_id=thread_id)
        await update_thread(thread_id=thread_id,
                            user_id=user_id,
                            name=chat_name)


        # Получаем ответ от GPT
        answer_text: str = await assistant.send_content_poll(content=content,
                                                             thread_id=thread_id)
        print(f'{answer_text=}')
        return TextResponse(
            status=GPTResponseStatus.succeed,
            answer_text=answer_text,
            thread_id=thread_id,
            chat_name=chat_name,
            created_db_thread_id=created_db_thread_id
        )

    async def prompt_by_text(self,
                             user_id: int,
                             language: str,
                             is_admin: bool,
                             text: str,
                             action_id: int,
                             thread_id: str | None) -> TextResponse:
        content: list[dict[str, Any]] = [{"type": "text", "text": text}]
        return await self.send_content_get_text(
            user_id=user_id,
            language=language,
            is_admin=is_admin,
            content=content,
            action_id=action_id,
            thread_id=thread_id
        )

    async def prompt_by_image(self,
                              user_id: int,
                              language: str,
                              is_admin: bool,
                              image_url: str,
                              caption: str | None,
                              action_id: int,
                              thread_id: str | None) -> TextResponse:
        caption = caption or (LANGUAGE_CAPTIONS.get(language) if language else None)
        return await self.send_content_get_text(
            user_id=user_id,
            content=ChatGPTVision().create_content(photo_urls=[image_url], caption=caption),
            action_id=action_id,
            thread_id=thread_id,
            language=language,
            is_admin=is_admin
        )

    async def prompt_by_audio(self,
                              user_id: int,
                              language: str,
                              is_admin: bool,
                              audio,
                              action_id: int,
                              thread_id: str | None,
                              filename: str | None = None,
                              audio_file_format: str = "ogg"):
        assistant_data: AssistantData | None = await self.__before_send_content(
            user_id=user_id, is_admin=is_admin, action_id=action_id
        )
        if not assistant_data:
            return TextResponse(status=GPTResponseStatus.not_enough_tokens)

        transcripted_audio_text: str = await ChatGPT4().transcript_audio_by_bytes(
            audio=(filename or f"voice-{user_id}.{audio_file_format}", audio)
        )
        return await self.prompt_by_text(
            user_id=user_id, action_id=action_id,
            text=transcripted_audio_text,
            is_admin=is_admin, language=language,
            thread_id=thread_id
        )
        # return await self.send_content_get_text(
        #     user_id=user_id, action_id=action_id,
        #     content=transcripted_audio_text,
        #     is_admin=is_admin, language=language,
        #     thread_id=thread_id
        # )

    async def prompt_by_images(self,
                               user_id: int,
                               language: str,
                               is_admin: bool,
                               images: list[str],
                               action_id: int,
                               thread_id: str,
                               caption: str | None = None
                               ):
        caption = caption or (LANGUAGE_CAPTIONS.get(language) if language else None)
        return await self.send_content_get_text(
            user_id=user_id,
            content=ChatGPTVision().create_content(photo_urls=images, caption=caption),
            action_id=action_id,
            thread_id=thread_id,
            language=language,
            is_admin=is_admin
        )

    async def generate_image(self,
                             user_id: int,
                             gpt_answer: str,
                             is_again: bool
                             ) -> ImageResponse:
        action = "generate_img"
        model = settings.admin_ai_settings.model_gen_img
        if is_again:
            language, is_admin = await get_user_values(user_id=user_id,
                                                       values=["language", "is_admin_bot"])
            if not is_admin:
                user_minus_request: UserMinusRequest = await self.minus_user_request(
                    user_id=user_id,
                    action=action,
                    is_admin=is_admin
                )
                if not user_minus_request.has_tokens:
                    return ImageResponse(
                        status=GPTResponseStatus.not_enough_tokens
                    )

                res = await get_model_by_action(user_id=user_id, action=action)
                if not res:
                    return ImageResponse(status=GPTResponseStatus.not_enough_tokens)

                model_id, model = res

        # Инициируем генератор изображений и генерируем изображения
        gpt_image_generator = ChatGPTImageGenerator(model=model, action=action)
        images = await gpt_image_generator.generate_images(prompt=gpt_answer, n=1)
        image = images[0].url
        try:
            image = await self.file_manager().upload_file_by_url_get_url(image_url=image,
                                                                         folder=self.file_manager.folders.GPT_GENERATE)
        except:
            pass

        return ImageResponse(
            status=GPTResponseStatus.succeed,
            image_url=image
        )

    async def get_user_gpt_threads(self, user_id: int,
                                   action_id: int | None = None,
                                   offset: int = 0, limit: int = 10) -> List[ThreadSchema]:
        threads: List[ThreadSchema] = await get_user_threads(user_id=user_id, action_id=action_id,
                                         offset=offset, limit=limit)
        return threads


    async def get_user_gpt_thread(self, user_id: int, thread_id: int) -> ThreadSchema | None:
        thread: ThreadSchema | None = await get_thread(
            user_id=user_id,
            thread_id=thread_id
        )
        return thread

    async def get_user_gpt_thread_messages(self, thread_id: str,
                                           offset_message_id: str,
                                           limit: int = 20):
        assistant = Assistant()
        return await assistant.get_thread_messages(
            thread_id=thread_id,
            offset_message_id=offset_message_id,
            limit=limit
        )

    async def get_user_gpt_thread_message(self, thread_id: str,
                                          message_id: str) -> Message:
        assistant = Assistant()
        return await assistant.get_message_by_id(thread_id, message_id)

    @default_cached
    async def get_gpt_assintants(self) -> List[GPTAssistantSchema]:
        return await get_all_assistants()

    @default_cached
    async def get_gpt_assinstant(self, id: int) -> GPTAssistantSchema:
        return await get_assistant(id)

    async def update_assistant_data(self, assistant_id: str,
                                    name: str | None = None,
                                    description: str | None = None,
                                    instructions: str | None = None):
        data = {}
        if name:
            data.update(name=name)
        if description:
            data.update(description=description)
        if instructions:
            data.update(instructions=instructions)

        if data:
            await Assistant().update_assistant_data(assistant_id=assistant_id, **data)

    async def update_assistants_data_from_db(self):
        assintants: List[GPTAssistantSchema] = await self.get_gpt_assintants()
        for assistant in assintants:
            print(f'{assistant.model_dump()=}')
            await self.update_assistant_data(assistant_id=assistant.assistant_id,
                                             name=assistant.name,
                                             description=assistant.description,
                                             instructions=assistant.instructions)

    async def add_photo_cloth_to_wardrobe(self,
                                          image: bytes,
                                          cloth_category_id: int,
                                          name: str,
                                          user_id: int) -> int:
        thread_id: str = await get_user_thread_id(user_id)

        filename = f"wardrobe_{user_id}"
        file_id: int = await Assistant().upload_images_to_thread_wardrobe(
            image=image, thread_id=thread_id,
            filename=filename + ".jpg"
        )
        image_url = await self.file_manager().upload_file_get_url(file=image,
                                                                  folder=self.file_manager.folders.GPT_PROMPT,
                                                                  filename=filename)

        return await add_wardrobe_element(wardrobe_element=AddWardrobeElement(
            image_url=image_url, gpt_file_id=file_id,
            name=name, cloth_category_id=cloth_category_id
        ), user_id=user_id)

    async def delete_wardrobe_element(self, wardrobe_element_id: int, user_id: int) -> WardrobeElementDeleted | None:
        we: WardrobeElementDeleted | None = await delete_wardrobe_element(
            wardrobe_element_id=wardrobe_element_id,
            user_id=user_id
        )
        if not we:
            raise Exception("Not Found")

        await Assistant().delete_file(file_id=we.gpt_file_id)
        return we



    async def get_user_wardrobe_elements(self, user_id: int,
                                         cloth_category_id: int | None = None,
                                         offset: int = 0,
                                         limit: int | None = None) -> List[WardrobeElementResponse]:
        return await get_user_wardrobe_elements(user_id=user_id,
                                                cloth_category_id=cloth_category_id,
                                                offset=offset, limit=limit)
    async def get_user_wardrobe_element(self, user_id: int, wardrobe_element_id: int) -> WardrobeElementResponse:
        return await get_user_wardrobe_element(user_id, wardrobe_element_id)

    async def delete_not_needed_files(self, user_id: int):
        elements = await self.get_user_wardrobe_elements(user_id=user_id)
        files_ids: list[str] = [el.gpt_file_id for el in elements]
        await Assistant().delete_not_needed_files(not_delete=files_ids)